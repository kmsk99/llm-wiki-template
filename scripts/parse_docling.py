#!/usr/bin/env python3
"""parse_docling.py — Docling 기반 raw/ 비텍스트 파일 → .parsed.md 변환

엔진: Docling (PDF, DOCX, PPTX, XLSX, 이미지, HTML 등 통합 처리)
  - macOS: OcrMac (Apple Vision) OCR
  - Linux: EasyOCR / Tesseract fallback
  - LLM: CLIProxyAPI (OpenAI-compatible) → Docling 내장 PictureDescriptionApiOptions

사용법:
  python scripts/parse_docling.py                             # raw/ 전체 스캔
  python scripts/parse_docling.py raw/files/file.pdf          # 단일 파일
  python scripts/parse_docling.py --no-llm raw/files/file.pdf # LLM 없이
  python scripts/parse_docling.py --no-ocr raw/files/file.pdf # OCR 없이
"""

import argparse
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
try:
    from env_defaults import env_or_dotenv
except ModuleNotFoundError:
    import importlib.util

    spec = importlib.util.spec_from_file_location("env_defaults_runtime", Path(__file__).with_name("env_defaults.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_defaults_runtime"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    env_or_dotenv = module.env_or_dotenv

# 초대형 이미지(포스터 등) decompression bomb 제한 해제
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------------------
# Docling imports
# ---------------------------------------------------------------------------
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# ---------------------------------------------------------------------------
# OCR 엔진 선택: macOS → OcrMac, 그 외 → EasyOCR fallback
# ---------------------------------------------------------------------------
def _build_ocr_options():
    if platform.system() == "Darwin":
        try:
            from docling.datamodel.pipeline_options import OcrMacOptions
            print("[OCR] OcrMac (Apple Vision)")
            return OcrMacOptions(
                lang=["ko-KR", "en-US", "ja-JP"],
            )
        except ImportError:
            pass
    # fallback
    try:
        from docling.datamodel.pipeline_options import EasyOcrOptions
        print("[OCR] EasyOCR (fallback)")
        return EasyOcrOptions()
    except ImportError:
        from docling.datamodel.pipeline_options import TesseractOcrOptions
        print("[OCR] Tesseract (fallback)")
        return TesseractOcrOptions()


# ---------------------------------------------------------------------------
# 변환기 생성
# ---------------------------------------------------------------------------
def create_converter(
    use_ocr: bool = True,
    use_llm: bool = False,
    llm_config: dict | None = None,
) -> DocumentConverter:
    pipeline_options = PdfPipelineOptions()

    # PDF 내장 텍스트 우선 사용 — 텍스트 레이어가 있으면 OCR/VLM보다 우선
    pipeline_options.force_backend_text = True

    # OCR 설정 — 텍스트 레이어 없는 순수 스캔 PDF용 fallback
    if use_ocr:
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = _build_ocr_options()
    else:
        pipeline_options.do_ocr = False

    # LLM 이미지 설명 — Docling 내장 PictureDescriptionApiOptions
    # CLIProxyAPI (OpenAI-compatible) 엔드포인트로 <!-- image --> 영역을 VLM 처리
    if use_llm and llm_config:
        try:
            from docling.datamodel.pipeline_options import PictureDescriptionApiOptions
            base_url = llm_config["base_url"].rstrip("/")
            pipeline_options.do_picture_description = True
            pipeline_options.picture_description_options = PictureDescriptionApiOptions(
                url=f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config['api_key']}"},
                params={"model": llm_config["model"]},
                timeout=llm_config.get("timeout", 300),
                prompt=(
                    "이 이미지에 보이는 내용을 한국어 Markdown으로 정확하게 변환하세요. "
                    "테이블은 Markdown 테이블로, 텍스트는 그대로 옮기세요. "
                    "이미지에 보이는 글자를 한 글자도 빠짐없이, 정확히 그대로 옮기세요. "
                    "추측하거나 내용을 바꾸지 마세요. 읽을 수 없는 부분은 [불명]으로 표시하세요."
                ),
            )
            pipeline_options.enable_remote_services = True
            print(f"[LLM] PictureDescription via {base_url} ({llm_config['model']})")
        except Exception as e:
            print(f"[WARN] PictureDescriptionApiOptions 설정 실패: {e}")

    pipeline_options.generate_picture_images = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    return converter


# ---------------------------------------------------------------------------
# PDF 텍스트 레이어 감지 + LLM Markdown 정리
# ---------------------------------------------------------------------------
def _pdf_has_text_layer(src: Path) -> str | None:
    """pdftotext로 PDF 텍스트 레이어 추출. 텍스트가 있으면 반환, 없으면 None."""
    try:
        result = subprocess.run(
            ["pdftotext", str(src), "-"],
            capture_output=True, text=True, timeout=30,
        )
        text = result.stdout.strip()
        # 의미 있는 텍스트가 50자 이상이면 텍스트 레이어로 판정
        if len(text) > 50:
            return text
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _llm_format_markdown(raw_text: str, filename: str, llm_config: dict) -> str:
    """추출된 raw 텍스트를 LLM으로 깔끔한 Markdown으로 정리."""
    try:
        import httpx
    except ImportError:
        print("[WARN] httpx 미설치 — raw 텍스트 그대로 반환")
        return raw_text

    base_url = llm_config["base_url"].rstrip("/")
    prompt = (
        "다음은 PDF에서 추출한 raw 텍스트입니다. "
        "내용을 변경하지 말고, 깔끔한 한국어 Markdown으로 정리해주세요.\n"
        "- 테이블은 Markdown 테이블로 변환\n"
        "- 제목/소제목은 적절한 헤딩(#, ##)으로\n"
        "- 숫자, 날짜, 고유명사는 원본 그대로 유지\n"
        "- 추측하거나 내용을 추가하지 마세요\n\n"
        f"파일: {filename}\n\n"
        f"```\n{raw_text}\n```"
    )

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {llm_config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": llm_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            },
            timeout=llm_config.get("timeout", 300),
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]

        # markdown 코드블록 벗기기
        if result.startswith("```markdown"):
            result = result[len("```markdown"):].strip()
        if result.startswith("```"):
            result = result[3:].strip()
        if result.endswith("```"):
            result = result[:-3].strip()

        print(f"[LLM] Markdown 정리 완료 ({llm_config['model']})")
        return result

    except Exception as e:
        print(f"[WARN] LLM Markdown 정리 실패: {e} — raw 텍스트 반환")
        return raw_text


# ---------------------------------------------------------------------------
# 병합 셀 중복 제거 — Excel 병합 셀이 풀리면서 동일 내용이 반복되는 문제 보정
# ---------------------------------------------------------------------------
def _dedup_table_row(cells: list[str]) -> list[str]:
    """연속으로 동일한 셀 값을 하나로 축소."""
    if not cells:
        return cells
    deduped = [cells[0]]
    for c in cells[1:]:
        if c.strip() != deduped[-1].strip():
            deduped.append(c)
    return deduped


def dedup_merged_cells(md: str) -> str:
    """Markdown 테이블에서 병합 셀로 인한 컬럼 중복을 제거."""
    lines = md.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 테이블 행 감지 (| ... | 패턴)
        if line.strip().startswith("|") and line.strip().endswith("|"):
            # 테이블 블록 수집
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i])
                i += 1

            if len(table_lines) < 2:
                result.extend(table_lines)
                continue

            # 각 행을 파싱
            parsed_rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                parsed_rows.append(cells)

            # 구분선(---) 행 확인
            sep_idx = None
            for idx, row in enumerate(parsed_rows):
                if all(re.match(r"^[-:]+$", c.strip()) for c in row if c.strip()):
                    sep_idx = idx
                    break

            # 중복 컬럼 수 판단: 헤더 행에서 동일 값이 반복되면 중복
            header = parsed_rows[0]
            unique_header = _dedup_table_row(header)

            if len(unique_header) < len(header):
                # 중복 있음 — 모든 행을 dedup
                deduped_rows = []
                for idx, row in enumerate(parsed_rows):
                    deduped_rows.append(_dedup_table_row(row))

                # 모든 행의 컬럼 수를 최대값에 맞춤 (빈 셀로 패딩)
                max_cols = max(len(row) for row in deduped_rows)
                for idx, row in enumerate(deduped_rows):
                    while len(row) < max_cols:
                        if sep_idx is not None and idx == sep_idx:
                            row.append("---")
                        else:
                            row.append("")

                # 구분선도 컬럼 수에 맞춤
                if sep_idx is not None:
                    deduped_rows[sep_idx] = ["---"] * max_cols

                for row in deduped_rows:
                    result.append("| " + " | ".join(row) + " |")
            else:
                result.extend(table_lines)
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


# ---------------------------------------------------------------------------
# 단일 파일 파싱
# ---------------------------------------------------------------------------
SUPPORTED_EXTS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".gif", ".tiff", ".bmp",
    ".html", ".htm", ".epub", ".csv",
}


def parse_file(
    converter: DocumentConverter,
    src: Path,
    use_llm: bool = False,
    llm_config: dict | None = None,
) -> bool:
    """단일 파일을 Docling으로 변환. 성공 시 True 반환."""
    ext = src.suffix.lower()

    # .parsed.md는 건드리지 않는다
    if src.name.endswith(".parsed.md"):
        return False

    if ext not in SUPPORTED_EXTS:
        print(f"[SKIP] 미지원 확장자: {src}")
        return False

    out = src.parent / f"{src.stem}.parsed.md"

    # 이미 파싱됨 + 원본이 새롭지 않으면 스킵
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        print(f"[SKIP] 이미 파싱됨: {out}")
        return False

    if out.exists():
        print(f"[REPARSE] 원본이 갱신됨: {src}")

    print(f"[PARSE] {src} → {out}")

    # PDF 텍스트 레이어 감지: 텍스트가 있으면 pdftotext + LLM 정리 경로
    if ext == ".pdf":
        raw_text = _pdf_has_text_layer(src)
        if raw_text:
            print("[ENGINE] pdftotext (텍스트 레이어 감지)")
            if use_llm and llm_config:
                md_content = _llm_format_markdown(raw_text, src.name, llm_config)
            else:
                md_content = raw_text
            md_content = dedup_merged_cells(md_content)
            out.write_text(md_content, encoding="utf-8")
            print(f"[DONE] {out}")
            return True
        else:
            print("[ENGINE] Docling (스캔 PDF — OCR+VLM)")

    else:
        print("[ENGINE] Docling")

    try:
        result = converter.convert(str(src))
        md_content = result.document.export_to_markdown()
    except Exception as e:
        print(f"[ERROR] Docling 변환 실패: {src} — {e}")
        return False

    # 병합 셀 중복 제거 (Excel 등)
    md_content = dedup_merged_cells(md_content)

    out.write_text(md_content, encoding="utf-8")
    print(f"[DONE] {out}")
    return True


# ---------------------------------------------------------------------------
# 디렉토리 스캔
# ---------------------------------------------------------------------------
def scan_directory(
    converter: DocumentConverter,
    raw_dir: Path,
    use_llm: bool = False,
    llm_config: dict | None = None,
) -> int:
    """raw/ 디렉토리를 재귀 스캔하여 비텍스트 파일을 파싱. 처리 건수 반환."""
    count = 0
    for src in sorted(raw_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name.startswith("."):
            continue
        if src.name.endswith(".parsed.md"):
            continue
        if src.suffix.lower() not in SUPPORTED_EXTS:
            continue
        try:
            parse_file(converter, src, use_llm=use_llm, llm_config=llm_config)
        except Exception as e:
            print(f"[ERROR] {src}: {e}")
        count += 1
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Docling 기반 raw/ 파싱")
    parser.add_argument("file", nargs="?", help="파싱할 단일 파일 경로")
    parser.add_argument("--no-llm", action="store_true", help="LLM 이미지 설명 비활성화")
    parser.add_argument("--no-ocr", action="store_true", help="OCR 비활성화")
    parser.add_argument(
        "--openai-base-url",
        default=env_or_dotenv("DOCLING_OPENAI_BASE_URL", env_or_dotenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1")),
    )
    parser.add_argument(
        "--openai-api-key",
        default=env_or_dotenv("DOCLING_OPENAI_API_KEY", env_or_dotenv("CLIPROXY_API_KEY", "marker-local")),
    )
    parser.add_argument(
        "--openai-model",
        default=env_or_dotenv("DOCLING_OPENAI_MODEL", "gpt-5.4-mini"),
    )
    parser.add_argument(
        "--llm-timeout", type=int,
        default=int(env_or_dotenv("DOCLING_LLM_TIMEOUT", "300") or "300"),
    )
    args = parser.parse_args()

    use_llm = not args.no_llm
    use_ocr = not args.no_ocr
    llm_config = None
    if use_llm:
        llm_config = {
            "base_url": args.openai_base_url,
            "api_key": args.openai_api_key,
            "model": args.openai_model,
            "timeout": args.llm_timeout,
        }

    converter = create_converter(use_ocr=use_ocr, use_llm=use_llm, llm_config=llm_config)

    if args.file:
        src = Path(args.file).resolve()
        if not src.exists():
            print(f"[ERROR] 파일을 찾을 수 없음: {src}")
            sys.exit(1)
        success = parse_file(converter, src, use_llm=use_llm, llm_config=llm_config)
        sys.exit(0 if success else 1)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        raw_dir = repo_root / "raw"
        print("=== raw/ 비텍스트 파일 스캔 ===")
        count = scan_directory(converter, raw_dir, use_llm=use_llm, llm_config=llm_config)
        if count == 0:
            print("파싱할 비텍스트 파일이 없습니다.")
        else:
            print(f"=== 완료: {count}개 파일 처리 ===")


if __name__ == "__main__":
    main()
