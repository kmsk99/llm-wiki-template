#!/usr/bin/env python3
"""Parse HWP/HWPX files into Markdown.

Strategy:
- HWPX or ZIP-backed HWP -> XML/text extraction (python-hwpx when available, stdlib fallback)
- Classic HWP v5 (CFB) -> libhwp extraction when available
- HTML masquerading as .hwp -> HTML text extraction fallback
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
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

HWP_CFB_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = b"PK\x03\x04"
HTML_PREFIXES = (b"<!doctype html", b"<html")
IMAGE_MAGIC = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".gif": b"GIF8",
    ".bmp": b"BM",
}
NS = {
    "hp": "http://www.hancom.co.kr/schema/owpml/2016/paragraph",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("out")
    return parser.parse_args()


def sniff_hwp_format(src: Path) -> str:
    raw_head = src.read_bytes()[:64].lstrip()
    head = raw_head.lower()
    if head.startswith(HTML_PREFIXES):
        return "html"
    if src.suffix.lower() == ".hwpx" or raw_head.startswith(ZIP_MAGIC):
        return "hwpx"
    if raw_head.startswith(HWP_CFB_MAGIC) or src.read_bytes()[:8] == HWP_CFB_MAGIC:
        return "hwp"
    return "unknown"


def collapse_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    result: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                result.append("")
            blank = True
            continue
        result.append(line)
        blank = False
    return "\n".join(result).strip()


def sanitize_text(text: str) -> str:
    return text.encode("utf-8", "replace").decode("utf-8")


def extract_html_text(src: Path) -> str:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return src.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(src.read_text(encoding="utf-8", errors="ignore"), "lxml")
    for tag in soup.select("script,style,noscript"):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return collapse_blank_lines(text)


def extract_hwpx_text_python_hwpx(src: Path) -> str:
    try:
        from hwpx import TextExtractor
    except Exception:
        return ""
    try:
        return collapse_blank_lines(TextExtractor(src).extract_text())
    except Exception:
        return ""


def iter_hwpx_section_names(zf: zipfile.ZipFile) -> Iterable[str]:
    names = sorted(name for name in zf.namelist() if re.match(r"Contents/section\d+\.xml$", name))
    return names


def extract_hwpx_text_zip(src: Path) -> str:
    parts: list[str] = []
    try:
        with zipfile.ZipFile(src) as zf:
            for name in iter_hwpx_section_names(zf):
                root = ET.fromstring(zf.read(name))
                for para in root.findall(".//hp:p", NS):
                    texts = [node.text or "" for node in para.findall(".//hp:t", NS)]
                    line = "".join(texts).strip()
                    if line:
                        parts.append(line)
    except Exception:
        return ""
    return collapse_blank_lines("\n".join(parts))


def extract_hwpx_preview_text(src: Path) -> str:
    try:
        with zipfile.ZipFile(src) as zf:
            if "Preview/PrvText.txt" not in zf.namelist():
                return ""
            data = zf.read("Preview/PrvText.txt")
            text = data.decode("utf-8", errors="ignore").strip()
            if not text:
                return ""
            printable_ratio = sum(ch.isprintable() or ch.isspace() for ch in text) / max(len(text), 1)
            if printable_ratio < 0.85:
                return ""
            return collapse_blank_lines(text)
    except Exception:
        return ""


def extract_hwpx_preview_image_text(src: Path) -> str:
    try:
        with zipfile.ZipFile(src) as zf:
            candidates = [
                n for n in zf.namelist()
                if (n.startswith("Preview/") or n.startswith("BinData/")) and n.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))
            ]
            name = None
            for candidate in candidates:
                data = zf.read(candidate)
                suffix = Path(candidate).suffix.lower()
                magic = IMAGE_MAGIC.get(suffix)
                if magic and data.startswith(magic):
                    name = candidate
                    break
            if not name:
                return ""
            suffix = Path(name).suffix or ".png"
            with tempfile.TemporaryDirectory() as tmpdir:
                image_path = Path(tmpdir) / f"preview{suffix}"
                image_path.write_bytes(zf.read(name))
                try:
                    from parse_image import build_markdown  # loaded by tests; available as sibling script at runtime
                except Exception:
                    import importlib.util, sys
                    spec = importlib.util.spec_from_file_location("parse_image_runtime", Path(__file__).with_name("parse-image.py"))
                    module = importlib.util.module_from_spec(spec)
                    sys.modules["parse_image_runtime"] = module
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    build_markdown = module.build_markdown
                markdown = build_markdown(
                    image_path,
                    use_llm=True,
                    base_url=env_or_dotenv(
                        "DOCLING_OPENAI_BASE_URL",
                        env_or_dotenv("MARKER_OPENAI_BASE_URL", env_or_dotenv("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1")),
                    ),
                    api_key=env_or_dotenv(
                        "DOCLING_OPENAI_API_KEY",
                        env_or_dotenv("MARKER_OPENAI_API_KEY", env_or_dotenv("CLIPROXY_API_KEY", "marker-local")),
                    ),
                    model=env_or_dotenv("DOCLING_OPENAI_MODEL", env_or_dotenv("MARKER_OPENAI_MODEL", "gpt-5.4-mini")),
                    timeout=int(env_or_dotenv("DOCLING_LLM_TIMEOUT", env_or_dotenv("MARKER_LLM_TIMEOUT", "300")) or "300"),
                )
                if "## Vision" in markdown and "TODO: GPT vision unavailable or empty" not in markdown:
                    return collapse_blank_lines("\n".join(markdown.splitlines()[markdown.splitlines().index("## Vision") + 1 :]))
    except Exception:
        return ""
    return ""


def extract_hwpx_text(src: Path) -> str:
    text = extract_hwpx_text_python_hwpx(src)
    if text:
        return text
    text = extract_hwpx_text_zip(src)
    if text:
        return text
    text = extract_hwpx_preview_text(src)
    if text:
        return text
    return extract_hwpx_preview_image_text(src)


def paragraph_text_from_chars(chars: Iterable[object]) -> str:
    out: list[str] = []
    for ch in chars:
        kind = getattr(ch, "kind", "")
        code = getattr(ch, "code", None)
        if kind == "char_code" and isinstance(code, int):
            out.append(chr(code))
        elif kind == "char_control" and code in (10, 13):
            out.append("\n")
    return "".join(out)


def extract_hwp_text(src: Path) -> str:
    libhwp_text = extract_hwp_text_libhwp(src)
    if libhwp_text and not libhwp_text.startswith("TODO:"):
        return libhwp_text
    hwp5txt_text = extract_hwp_text_hwp5txt(src)
    if hwp5txt_text:
        return hwp5txt_text
    preview_text = extract_hwp_preview_text(src)
    if preview_text:
        return preview_text
    return libhwp_text or "TODO: HWP 바이너리 파서를 사용할 수 없습니다."


def extract_hwp_text_libhwp(src: Path) -> str:
    try:
        from libhwp import HWPReader
    except Exception as exc:
        return f"TODO: HWP 바이너리 파서를 불러오지 못했습니다 ({exc})"
    try:
        reader = HWPReader(str(src))
        parts: list[str] = []
        for section in reader.sections:
            for para in getattr(section, "paragraphs", []):
                line = paragraph_text_from_chars(getattr(para, "chars", [])).strip()
                if line:
                    parts.append(line)
        text = collapse_blank_lines("\n".join(parts))
        return text or "TODO: HWP 텍스트를 추출했지만 비어 있습니다."
    except BaseException as exc:
        return f"TODO: HWP 바이너리 파싱 실패 ({type(exc).__name__}: {exc})"


def extract_hwp_text_hwp5txt(src: Path) -> str:
    cli = shutil.which("hwp5txt")
    if not cli:
        return ""
    proc = subprocess.run(
        [cli, str(src)],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return ""
    text = collapse_blank_lines(proc.stdout)
    return sanitize_text(text) if text else ""


def extract_hwp_preview_text(src: Path) -> str:
    try:
        import olefile
    except Exception:
        return ""
    try:
        ole = olefile.OleFileIO(str(src))
    except Exception:
        return ""
    try:
        if not ole.exists("PrvText"):
            return ""
        data = ole.openstream("PrvText").read()
        text = data.decode("utf-16le", errors="ignore").replace("\x00", "").strip()
        return sanitize_text(collapse_blank_lines(text)) if text else ""
    except Exception:
        return ""
    finally:
        try:
            ole.close()
        except Exception:
            pass


def build_markdown(src: Path) -> str:
    fmt = sniff_hwp_format(src)
    if fmt == "hwpx":
        body = extract_hwpx_text(src)
        title = "HWPX Parse"
    elif fmt == "hwp":
        body = extract_hwp_text(src)
        title = "HWP Parse"
    elif fmt == "html":
        body = extract_html_text(src)
        title = "HWP HTML Fallback"
    else:
        body = "TODO: 지원하지 않는 HWP 포맷이거나 시그니처를 식별하지 못했습니다."
        title = "HWP Parse"

    lines = [
        f"# {title}",
        "",
        f"- Source: {src.name}",
        f"- Detected format: {fmt}",
        "",
        sanitize_text(body.strip() if body.strip() else "TODO: 추출된 텍스트가 없습니다."),
    ]
    return sanitize_text(collapse_blank_lines("\n".join(lines)) + "\n")


def main() -> int:
    args = parse_args()
    src = Path(args.src)
    out = Path(args.out)
    out.write_text(build_markdown(src), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
