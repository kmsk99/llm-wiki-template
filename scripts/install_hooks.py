#!/usr/bin/env python3
"""Install a managed hook without replacing an unrelated pre-commit hook."""
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
MARKER = "# llm-wiki-template managed pre-commit"

def main():
    result = subprocess.run(["git", "rev-parse", "--git-path", "hooks/pre-commit"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print("Git 저장소가 필요합니다. git init 후 다시 실행하세요.", file=sys.stderr)
        return 1
    target = Path(result.stdout.strip())
    if not target.is_absolute(): target = ROOT / target
    if target.is_symlink() or (target.exists() and MARKER not in target.read_text()):
        print("기존 pre-commit을 보존했습니다. scripts/hooks/pre-commit 호출을 기존 훅에 연결하세요.", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('#!/bin/sh\n' + MARKER + '\nexec sh "$(git rev-parse --show-toplevel)/scripts/hooks/pre-commit"\n')
    target.chmod(0o755)
    print("원자료 보호·시크릿 검사 훅 설치 완료")
    return 0
if __name__ == "__main__": sys.exit(main())
