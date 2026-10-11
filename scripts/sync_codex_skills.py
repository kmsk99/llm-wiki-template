#!/usr/bin/env python3
"""Generate project-local skills from .claude/commands; --check detects drift."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
COMMANDS = REPO / ".claude/commands"

# 이 스크립트가 만든 스킬만 지우거나 덮어쓴다. 사용자가 손으로 넣은 로컬
# 스킬을 동명이인이라는 이유로 날리면 복구할 길이 없다.
MARKER = "<!-- generated-by: scripts/sync_codex_skills.py -->"

NOTICE = """{marker}

> 정본은 볼트 루트의 `.claude/commands/{name}.md`이고 이 파일은
> `scripts/sync_codex_skills.py` 가 만든 복사본이라 직접 고치면 다음 동기화에
> 덮여 사라진다.
"""


def codex_skills_root() -> Path:
    return REPO / ".agents/skills"


def render(source: Path) -> str:
    """정본 커맨드를 codex 스킬 본문으로 바꾼다."""
    text = source.read_text(encoding="utf-8")
    name = source.stem

    match = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    if not match:
        raise SystemExit(f"frontmatter 없음: {source.relative_to(REPO)}")
    front, body = match.group(1), text[match.end():]

    if not re.search(r'^description:[ \t]*\S', front, re.MULTILINE):
        raise SystemExit(f"description 없음: {source.relative_to(REPO)}")

    notice = NOTICE.format(marker=MARKER, name=name)
    return f"---\n{front}---\n\n{notice}\n{body.lstrip()}"


def managed(skill_dir: Path) -> bool:
    target = skill_dir / "SKILL.md"
    if target.is_symlink() or not target.is_file():
        return False
    return MARKER in target.read_text(encoding="utf-8")


def scan(apply: bool) -> tuple[list[str], int, int]:
    """정본과 사본을 대조한다. `apply` 면 어긋난 곳을 그 자리에서 고친다.

    감사 스크립트가 `apply=False` 로 불러 쓰므로 출력 없이 목록만 돌려준다.
    """
    root = codex_skills_root()
    if not root.resolve().is_relative_to(REPO):
        raise SystemExit(f"볼트 밖을 가리키는 스킬 루트: {root}")
    sources = sorted(COMMANDS.glob("*.md"))
    if not sources:
        raise SystemExit(f"정본 커맨드가 없다: {COMMANDS}")

    drift: list[str] = []
    wrote = 0

    for source in sources:
        name = source.stem
        target = root / name / "SKILL.md"
        want = render(source)

        if not target.parent.resolve().is_relative_to(REPO):
            drift.append(f"볼트 밖을 가리키는 스킬 경로: {target.parent}")
            continue

        if target.is_symlink():
            # 기존 어댑터 중 자기 정본으로 연결된 링크만 실파일로 전환한다.
            if target.resolve() != source.resolve():
                drift.append(f"다른 파일을 가리키는 스킬 심링크: {target}")
                continue
            drift.append(f"심링크라 codex 가 무시한다: {target}")
            if apply:
                target.unlink()
            else:
                continue

        have = target.read_text(encoding="utf-8") if target.is_file() else None
        if have == want:
            continue

        if have is not None and MARKER not in have:
            drift.append(f"이 스크립트가 만들지 않은 동명 스킬이 있다: {target}")
            continue

        drift.append(f"{'없음' if have is None else '오래됨'}: {name}")
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(want, encoding="utf-8")
            wrote += 1

    # 정본에서 사라진 생성 파일만 정리하고 별도 리소스는 보존한다.
    names = {s.stem for s in sources}
    if root.is_dir():
        for skill_dir in sorted(root.iterdir()):
            if skill_dir.is_symlink() or not skill_dir.is_dir() or skill_dir.name in names:
                continue
            if managed(skill_dir):
                drift.append(f"정본에 없는 잔여 스킬: {skill_dir.name}")
                if apply:
                    (skill_dir / "SKILL.md").unlink()
                    if not any(skill_dir.iterdir()):
                        skill_dir.rmdir()

    return drift, wrote, len(sources)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="복사하지 않고 정본과 어긋난 곳만 보고한다")
    args = parser.parse_args()

    drift, wrote, total = scan(apply=not args.check)
    root = codex_skills_root()

    if args.check:
        if drift:
            print(f"codex 스킬 동기화 필요 ({len(drift)}건):")
            for line in drift:
                print(f"  - {line}")
            print("\n  python3 scripts/sync_codex_skills.py")
            return 1
        print(f"프로젝트 스킬 동기화됨: {total}개 ({root})")
        return 0

    print(f"프로젝트 스킬 {wrote}개 갱신 / 전체 {total}개 → {root}")
    for line in drift:
        print(f"  - {line}")
    return 1 if scan(apply=False)[0] else 0


if __name__ == "__main__":
    sys.exit(main())
