#!/usr/bin/env python3
"""parse-pdf.py — PDF → Markdown using opendataloader-pdf + CLIPROXY image captions.

Pipeline:
  1. `opendataloader-pdf -f markdown-with-images --image-output external -o <tmp> <pdf>`
  2. Read the produced Markdown, locate every extracted image reference
  3. Send each image to CLIPROXY (`/chat/completions`) for a Korean caption
  4. Replace the image link with the caption (inline, under a heading)
  5. Write final Markdown to `<pdf_stem>.parsed.md` next to the source
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from urllib.request import Request, urlopen

try:
    from env_defaults import env_or_dotenv
except ModuleNotFoundError:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "env_defaults_runtime", Path(__file__).with_name("env_defaults.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_defaults_runtime"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    env_or_dotenv = module.env_or_dotenv


DEFAULT_BASE_URL = env_or_dotenv(
    "DOCLING_OPENAI_BASE_URL",
    env_or_dotenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
)
DEFAULT_API_KEY = env_or_dotenv(
    "DOCLING_OPENAI_API_KEY",
    env_or_dotenv("CLIPROXY_API_KEY", "marker-local"),
)
DEFAULT_MODEL = env_or_dotenv("DOCLING_OPENAI_MODEL", "gpt-5.4-mini")
DEFAULT_TIMEOUT = int(env_or_dotenv("DOCLING_LLM_TIMEOUT", "300") or "300")

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_PROMPT = (
    "이 이미지에 보이는 내용을 한국어 Markdown으로 정확하게 옮기세요.\n"
    "- 보이는 텍스트는 가능한 한 그대로 전사하세요.\n"
    "- 표가 있으면 Markdown 표로 구조화하세요.\n"
    "- 차트/도표는 축 라벨, 범례, 추세를 설명하세요.\n"
    "- 사진이라면 무엇이 찍혀 있는지 한 문장으로 서술하세요.\n"
    "- 읽을 수 없는 부분은 [불명]으로 표시하세요.\n"
    "- 추측하거나 없는 내용을 만들지 마세요.\n"
    "- 최종 답변은 설명 본문만 출력하세요. 코드블록 없이."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="opendataloader-pdf + CLIPROXY 캡션")
    parser.add_argument("src", help="입력 PDF 파일 경로")
    parser.add_argument("out", nargs="?", help="출력 .parsed.md 경로 (기본: src 옆)")
    parser.add_argument("--no-llm", action="store_true", help="이미지 캡션 생략")
    parser.add_argument(
        "--image-format", default="jpeg", choices=["jpeg", "png"],
        help="opendataloader-pdf 이미지 포맷"
    )
    parser.add_argument(
        "--hybrid", action="store_true",
        help="opendataloader-pdf-hybrid 서버를 기동해 수식(LaTeX) 추출",
    )
    parser.add_argument(
        "--no-hybrid", dest="hybrid", action="store_false",
        help="하이브리드 비활성화 (기본값)",
    )
    parser.add_argument("--hybrid-port", type=int, default=5002, help="하이브리드 서버 포트")
    parser.add_argument(
        "--hybrid-url", default=None,
        help="이미 실행 중인 하이브리드 서버 URL (자동 기동 건너뜀)"
    )
    parser.add_argument(
        "--hybrid-device", default="auto",
        choices=["auto", "cpu", "cuda", "mps", "xpu"],
        help="하이브리드 서버 연산 장치",
    )
    parser.add_argument(
        "--hybrid-startup-timeout", type=int, default=180,
        help="하이브리드 서버 기동 대기 시간(초)",
    )
    parser.add_argument("--openai-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--openai-api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--openai-model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return parser.parse_args()


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _find_hybrid_bin() -> str:
    cli = shutil.which("opendataloader-pdf-hybrid")
    if cli:
        return cli
    venv_cli = Path(sys.executable).parent / "opendataloader-pdf-hybrid"
    if venv_cli.exists():
        return str(venv_cli)
    raise RuntimeError(
        "opendataloader-pdf-hybrid CLI를 찾을 수 없습니다. "
        "pip install 'opendataloader-pdf[hybrid]' 후 재시도하세요."
    )


@contextmanager
def hybrid_server(
    *, port: int, device: str, startup_timeout: int
) -> Iterator[str]:
    """하이브리드 서버를 생성/재사용. yield 로 base URL 전달."""
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    if _port_open(host, port):
        print(f"[HYBRID] 기존 서버 재사용: {url}")
        yield url
        return

    cli = _find_hybrid_bin()
    cmd = [
        cli,
        "--host", host,
        "--port", str(port),
        "--device", device,
        "--enrich-formula",
        "--no-enrich-picture-description",  # 이미지 캡션은 CLIPROXY가 담당
        "--log-level", "warning",
    ]
    print(f"[HYBRID] 서버 기동 ({device}, port {port}) — 최초 실행 시 모델 다운로드로 수 분 소요")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        deadline = time.time() + startup_timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"하이브리드 서버가 즉시 종료되었습니다 (exit {proc.returncode}). "
                    f"'opendataloader-pdf-hybrid --port {port}'을 수동 실행해 오류를 확인하세요."
                )
            if _port_open(host, port):
                print(f"[HYBRID] 준비 완료: {url}")
                break
            time.sleep(2)
        else:
            raise RuntimeError(
                f"하이브리드 서버 기동 대기 초과 ({startup_timeout}s). "
                f"수동 기동을 권장합니다: opendataloader-pdf-hybrid --port {port} --enrich-formula"
            )
        yield url
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def run_opendataloader(
    src: Path,
    workdir: Path,
    image_format: str,
    *,
    hybrid_url: Optional[str] = None,
) -> Path:
    """opendataloader-pdf 실행. 생성된 .md 경로 반환."""
    cli = shutil.which("opendataloader-pdf")
    if not cli:
        # venv fallback — parse-raw.sh가 activate를 해주지만 직접 실행 대비
        venv_cli = Path(sys.executable).parent / "opendataloader-pdf"
        if venv_cli.exists():
            cli = str(venv_cli)
        else:
            raise RuntimeError(
                "opendataloader-pdf CLI를 찾을 수 없습니다. "
                "pip install opendataloader-pdf 후 재시도하세요."
            )

    cmd = [
        cli,
        "-f", "markdown-with-images",
        "--image-output", "external",
        "--image-format", image_format,
        "-o", str(workdir),
        "-q",
    ]
    if hybrid_url:
        cmd += [
            "--hybrid", "docling-fast",
            "--hybrid-mode", "auto",
            "--hybrid-url", hybrid_url,
            "--hybrid-fallback",
            "--hybrid-timeout", "0",
        ]
        print(f"[ENGINE] opendataloader-pdf ({image_format}) + hybrid {hybrid_url}")
    else:
        print(f"[ENGINE] opendataloader-pdf ({image_format})")
    cmd.append(str(src))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"opendataloader-pdf 실행 실패 (exit {result.returncode})\n"
            f"stderr: {result.stderr.strip()}"
        )

    md_files = sorted(workdir.rglob("*.md"))
    if not md_files:
        raise RuntimeError(f"opendataloader-pdf가 Markdown을 생성하지 않았습니다: {workdir}")
    # 입력 PDF 이름과 매칭되는 .md를 우선 선택
    preferred = [p for p in md_files if p.stem == src.stem]
    return preferred[0] if preferred else md_files[0]


def mime_type_for(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "image/png"


def build_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type_for(path)};base64,{encoded}"


def strip_code_fences(text: str) -> str:
    result = text.strip()
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    elif result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()
    return result


def extract_message_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("빈 choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return strip_code_fences(content)
    if isinstance(content, list):
        parts = [
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if parts:
            return strip_code_fences("\n".join(parts))
    raise ValueError("지원하지 않는 content 형식")


def caption_image(
    image_path: Path,
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
) -> tuple[Optional[str], Optional[str]]:
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": IMAGE_PROMPT},
                    {"type": "image_url", "image_url": {"url": build_data_url(image_path)}},
                ],
            }
        ],
    }
    try:
        req = Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return extract_message_text(payload), None
    except Exception as exc:
        return None, str(exc)


def rewrite_markdown(
    md_text: str,
    md_path: Path,
    *,
    use_llm: bool,
    llm_config: Optional[dict],
) -> tuple[str, int, int]:
    """이미지 링크를 캡션으로 치환. (새 Markdown, 처리 수, 실패 수) 반환."""
    processed = 0
    failed = 0
    cache: dict[str, str] = {}

    def resolve(ref: str) -> Optional[Path]:
        if ref.startswith(("http://", "https://", "data:")):
            return None
        candidate = (md_path.parent / ref).resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    def replace(match: re.Match) -> str:
        nonlocal processed, failed
        alt = match.group(1).strip()
        ref = match.group(2).strip()
        image_path = resolve(ref)
        if image_path is None:
            # 외부 링크는 그대로 유지
            return match.group(0)

        processed += 1
        key = f"{image_path}:{image_path.stat().st_size}"
        if key in cache:
            caption = cache[key]
        elif not use_llm or llm_config is None:
            caption = f"[이미지: {alt or image_path.name}]"
        else:
            text, err = caption_image(image_path, **llm_config)
            if text:
                caption = text.strip()
                cache[key] = caption
            else:
                failed += 1
                caption = f"[이미지 캡션 실패: {alt or image_path.name} — {err or 'unknown'}]"

        label = alt or image_path.name
        return f"\n> **[이미지] {label}**\n>\n> {caption.replace(chr(10), chr(10) + '> ')}\n"

    new_md = IMAGE_PATTERN.sub(replace, md_text)
    return new_md, processed, failed


def main() -> int:
    args = parse_args()
    src = Path(args.src).resolve()
    if not src.exists():
        print(f"[ERROR] 파일을 찾을 수 없음: {src}", file=sys.stderr)
        return 1
    if src.suffix.lower() != ".pdf":
        print(f"[ERROR] PDF 파일이 아님: {src}", file=sys.stderr)
        return 1

    out_path = Path(args.out).resolve() if args.out else src.with_name(f"{src.stem}.parsed.md")

    use_llm = not args.no_llm
    llm_config = None
    if use_llm:
        llm_config = {
            "base_url": args.openai_base_url,
            "api_key": args.openai_api_key,
            "model": args.openai_model,
            "timeout": args.timeout,
        }
        print(f"[LLM] CLIPROXY {llm_config['base_url']} ({llm_config['model']})")
    else:
        print("[LLM] disabled (--no-llm)")

    def _parse(hybrid_url: Optional[str]) -> tuple[str, int, int]:
        with tempfile.TemporaryDirectory(prefix="odl-pdf-") as tmp:
            workdir = Path(tmp)
            md_path = run_opendataloader(
                src, workdir, args.image_format, hybrid_url=hybrid_url
            )
            md_text = md_path.read_text(encoding="utf-8")
            return rewrite_markdown(
                md_text, md_path, use_llm=use_llm, llm_config=llm_config
            )

    if args.hybrid_url:
        new_md, processed, failed = _parse(args.hybrid_url.rstrip("/"))
    elif args.hybrid:
        with hybrid_server(
            port=args.hybrid_port,
            device=args.hybrid_device,
            startup_timeout=args.hybrid_startup_timeout,
        ) as url:
            new_md, processed, failed = _parse(url)
    else:
        new_md, processed, failed = _parse(None)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(new_md, encoding="utf-8")
    print(
        f"[DONE] {out_path} "
        f"(이미지 {processed}개 처리, 실패 {failed}개)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
