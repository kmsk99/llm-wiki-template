#!/usr/bin/env python3
"""Parse image files into Markdown using local metadata + OCR.

This script is a repo-local fallback for raw image parsing because the
installed MarkItDown core only returns EXIF metadata for standalone images
unless an LLM client/model is configured.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("out")
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


def build_markdown(src: Path) -> str:
    lines = [
        "# Image Parse",
        "",
        f"- Source: {src.name}",
    ]

    lines.extend(load_image_metadata(src))

    ocr_text, ocr_error = run_tesseract(src)
    lines.extend(["", "## OCR", ""])
    if ocr_text:
        lines.append(ocr_text)
    else:
        lines.append(f"TODO: OCR unavailable or empty ({ocr_error or 'unknown error'})")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    src = Path(args.src)
    out = Path(args.out)
    out.write_text(build_markdown(src), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
