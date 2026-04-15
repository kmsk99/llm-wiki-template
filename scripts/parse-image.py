#!/usr/bin/env python3
"""Parse standalone image files into Markdown using direct GPT vision first.

Fallback order:
1. GPT vision via OpenAI-compatible `/chat/completions`
2. Local OCR (tesseract)
3. Metadata-only TODO output
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen
try:
    from env_defaults import env_or_dotenv
except ModuleNotFoundError:
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("env_defaults_runtime", Path(__file__).with_name("env_defaults.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_defaults_runtime"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    env_or_dotenv = module.env_or_dotenv


DEFAULT_BASE_URL = env_or_dotenv(
    "DOCLING_OPENAI_BASE_URL",
    env_or_dotenv("MARKER_OPENAI_BASE_URL", env_or_dotenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1")),
)
DEFAULT_API_KEY = env_or_dotenv(
    "DOCLING_OPENAI_API_KEY",
    env_or_dotenv("MARKER_OPENAI_API_KEY", env_or_dotenv("CLIPROXY_API_KEY", "marker-local")),
)
DEFAULT_MODEL = env_or_dotenv("DOCLING_OPENAI_MODEL", env_or_dotenv("MARKER_OPENAI_MODEL", "gpt-5.4-mini"))
DEFAULT_TIMEOUT = int(env_or_dotenv("DOCLING_LLM_TIMEOUT", env_or_dotenv("MARKER_LLM_TIMEOUT", "300")) or "300")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("out")
    parser.add_argument("--openai-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--openai-api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--openai-model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--no-llm", action="store_true", help="Skip GPT vision and use local OCR fallback only.")
    return parser.parse_args()


def load_image_metadata(src: Path) -> list[str]:
    lines: list[str] = []

    try:
        from PIL import Image
    except Exception:
        Image = None

    if Image is not None:
        with Image.open(src) as img:
            lines.append(f"- Format: {img.format or 'unknown'}")
            lines.append(f"- Dimensions: {img.width} x {img.height}")
            lines.append(f"- Mode: {img.mode}")

            if img.info:
                for key in ("dpi", "icc_profile", "transparency", "gamma"):
                    value = img.info.get(key)
                    if value:
                        if key == "icc_profile":
                            value = "present"
                        lines.append(f"- {key}: {value}")

    exiftool = shutil.which("exiftool")
    if exiftool:
        proc = subprocess.run(
            [exiftool, "-json", str(src)],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                payload = json.loads(proc.stdout)[0]
            except Exception:
                payload = {}
            for key in (
                "Title",
                "Caption",
                "Description",
                "Keywords",
                "Author",
                "Artist",
                "CreateDate",
                "DateTimeOriginal",
                "ImageSize",
            ):
                value = payload.get(key)
                if value:
                    lines.append(f"- {key}: {value}")

    return lines


def mime_type_for(src: Path) -> str:
    return mimetypes.guess_type(src.name)[0] or "image/png"


def build_data_url(src: Path) -> str:
    encoded = base64.b64encode(src.read_bytes()).decode("ascii")
    return f"data:{mime_type_for(src)};base64,{encoded}"


def strip_code_fences(text: str) -> str:
    result = text.strip()
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    elif result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()
    return result


def extract_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("No choices in LLM response")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return strip_code_fences(content)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(str(item["text"]))
        if parts:
            return strip_code_fences("\n".join(parts))
    raise ValueError("Unsupported LLM content shape")


def call_gpt_vision(src: Path, *, base_url: str, api_key: str, model: str, timeout: int) -> tuple[Optional[str], Optional[str]]:
    prompt = (
        "이 이미지에 보이는 내용을 한국어 Markdown으로 정확하게 옮기세요.\n"
        "- 보이는 텍스트는 가능한 한 그대로 전사하세요.\n"
        "- 제목/소제목은 Markdown 헤딩으로 정리하세요.\n"
        "- 표나 일정표가 보이면 Markdown 표나 목록으로 구조화하세요.\n"
        "- 포스터라면 날짜, 장소, 접수기간, 문의처, 신청방법을 우선 추출하세요.\n"
        "- 읽을 수 없는 부분은 [불명]으로 표시하세요.\n"
        "- 추측하거나 없는 내용을 만들지 마세요.\n"
        "- 최종 답변은 Markdown 본문만 출력하세요."
    )

    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": build_data_url(src)}},
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


def get_tesseract_lang() -> str | None:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return None

    proc = subprocess.run(
        [tesseract, "--list-langs"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None

    langs = {
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip() and "languages" not in line.lower()
    }
    if {"kor", "eng"} <= langs:
        return "kor+eng"
    if "eng" in langs:
        return "eng"
    if langs:
        return "+".join(sorted(langs))
    return None


def run_tesseract(src: Path) -> tuple[str | None, str | None]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return None, "tesseract not installed"

    lang = get_tesseract_lang()
    attempts = [
        ["--psm", "6"],
        ["--psm", "11"],
    ]

    last_error: str | None = None
    for extra in attempts:
        cmd = [tesseract, str(src), "stdout", *extra]
        if lang:
            cmd.extend(["-l", lang])
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )
        if proc.returncode == 0:
            text = proc.stdout.strip()
            if text:
                return text, None
            last_error = "ocr returned empty text"
        else:
            last_error = (proc.stderr or proc.stdout).strip() or "tesseract failed"

    return None, last_error


def is_auth_error(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    return "401" in lowered or "unauthorized" in lowered or "authentication" in lowered


def build_markdown(
    src: Path,
    *,
    use_llm: bool,
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
) -> str:
    lines = [
        "# Image Parse",
        "",
        f"- Source: {src.name}",
    ]

    lines.extend(load_image_metadata(src))

    llm_text: Optional[str] = None
    llm_error: Optional[str] = None
    if use_llm:
        llm_text, llm_error = call_gpt_vision(
            src,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )

    lines.extend(["", "## Vision", ""])
    if llm_text:
        lines.append(llm_text)
    else:
        if is_auth_error(llm_error):
            lines.append(f"TODO: GPT vision authentication failed ({llm_error or 'unknown error'})")
            lines.append("GPT OAuth에 다시 로그인한 뒤 재시도하세요.")
            return "\n".join(lines).rstrip() + "\n"
        lines.append(f"TODO: GPT vision unavailable or empty ({llm_error or 'unknown error'})")

    ocr_text, ocr_error = run_tesseract(src)
    if not llm_text:
        lines.extend(["", "## OCR Fallback", ""])
        if ocr_text:
            lines.append(ocr_text)
        else:
            lines.append(f"TODO: OCR unavailable or empty ({ocr_error or 'unknown error'})")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    src = Path(args.src)
    out = Path(args.out)
    out.write_text(
        build_markdown(
            src,
            use_llm=not args.no_llm,
            base_url=args.openai_base_url,
            api_key=args.openai_api_key,
            model=args.openai_model,
            timeout=args.timeout,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
