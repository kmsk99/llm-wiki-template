#!/usr/bin/env python3
"""Install core checks only; no LLM, graph or parser dependencies."""
from pathlib import Path
import subprocess
import sys
import venv
ROOT = Path(__file__).resolve().parents[1]
def main():
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(target)
    subprocess.run([str(python), "-c", "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'"], check=True)
    for command in [
        [str(python), "-m", "pip", "install", "-r", "scripts/requirements-core.txt"],
        [str(python), "scripts/sync_codex_skills.py"],
        [str(python), "scripts/install_hooks.py"],
        [str(python), "scripts/lint_wiki.py", "--check"],
    ]:
        subprocess.run(command, cwd=ROOT, check=True)
    print("기본 설치 완료. .venv의 Python으로 검사 명령을 실행하세요.")
if __name__ == "__main__": main()
