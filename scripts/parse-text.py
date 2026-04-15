#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def read_text_file(src: Path) -> str:
    raw = src.read_bytes()
    for encoding in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore").strip()


def read_doc_file(src: Path) -> str:
    textutil = shutil.which("textutil")
    if not textutil:
        return "TODO: .doc 파싱을 지원하는 시스템 도구(textutil)를 찾지 못했습니다."
    result = subprocess.run(
        [textutil, "-convert", "txt", "-stdout", str(src)],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "").strip()
    if output:
        return output
    stderr = (result.stderr or "").strip()
    if stderr:
        return f"TODO: .doc 텍스트 추출 실패 ({stderr})"
    return "TODO: .doc에서 텍스트를 추출하지 못했습니다."


def build_markdown(src: Path) -> str:
    suffix = src.suffix.lower()
    if suffix == ".txt":
        body = read_text_file(src)
    elif suffix == ".doc":
        body = read_doc_file(src)
    else:
        body = "TODO: 지원하지 않는 텍스트 계열 형식입니다."
    if not body:
        body = "TODO: 추출된 텍스트가 없습니다."
    return f"# {src.stem}\n\n{body}\n"


def main(src: str, out: str) -> int:
    src_path = Path(src)
    out_path = Path(out)
    out_path.write_text(build_markdown(src_path), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
