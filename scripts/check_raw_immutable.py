#!/usr/bin/env python3
"""Block staged raw mutations; additions and manifest content edits are allowed."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BLOCKED = {"M": "수정", "D": "삭제", "T": "파일 유형 변경", "U": "미해결 충돌"}

# 매니페스트는 raw 밑에 살지만 원자료가 아니라 **원자료에 대한 장부**다.
# `/catalog` 이 소스를 등록할 때마다 행을 더하고 `/ingest` 가 인제스트 상태를
# 갱신한다 — 즉 설계상 계속 바뀌어야 하는 파일이다. 여기를 막으면 스킬이
# 시키는 일을 커밋할 수 없어 매번 ALLOW_RAW_MUTATION 우회를 부르고, 우회가
# 일상이 되면 정작 원자료 수정도 함께 통과한다.
# 수정만 허용한다. 삭제·이름변경은 그대로 막는다 — 장부가 사라지면 그 도메인의
# 원자료가 무엇이었는지 알 방법이 없다.
MANIFEST = ".manifest.md"


def changed(mode: str) -> list[tuple[str, str]]:
    """(상태문자, 경로) 목록. raw/ 밑만 본다."""
    # NUL 구분으로 한글·탭·줄바꿈 경로도 손실 없이 읽는다. rename은 D+A로
    # 검사해 raw 밖으로 이동하거나 manifest로 이름을 바꾸어도 원본 D를 막는다.
    cmd = ["git", "diff", "--name-status", "-z", "--no-renames"]
    if mode == "staged":
        cmd.append("--cached")
    else:
        # 둘을 합쳐야 staged 변조를 작업 트리에서만 되돌려도 누락되지 않는다.
        staged = changed("staged")
        result = subprocess.run(cmd + ["--", "raw/"], cwd=REPO,
                                capture_output=True, text=True, check=True)
        fields = result.stdout.rstrip("\0").split("\0") if result.stdout else []
        return staged + list(zip(fields[::2], fields[1::2]))
    out = subprocess.run(cmd + ["--", "raw/"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    rows = []
    fields = out.rstrip("\0").split("\0") if out else []
    for status, path in zip(fields[::2], fields[1::2]):
        rows.append((status, path))
    return rows


def main() -> int:
    mode = "worktree" if "--worktree" in sys.argv else "staged"
    try:
        changes = changed(mode)
    except (OSError, subprocess.CalledProcessError):
        print("⛔ raw/ 변경 목록을 읽지 못했다 — 검사를 통과시키지 않는다.", file=sys.stderr)
        return 2
    violations = [(s, p) for s, p in changes
                  if s in BLOCKED
                  and not (s == "M" and Path(p).name == MANIFEST)]

    if not violations:
        return 0

    if os.environ.get("ALLOW_RAW_MUTATION") == "1":
        print("⚠️  raw/ 불변 규칙을 ALLOW_RAW_MUTATION=1 로 우회했다 "
              f"({len(violations)}건). 사유를 문서에 남겼는지 확인할 것.",
              file=sys.stderr)
        for s, p in violations:
            print(f"    {BLOCKED[s]}: {p}", file=sys.stderr)
        return 0

    print(f"\n⛔ raw/ 불변 규칙 위반 {len(violations)}건 — 커밋을 중단한다.\n")
    for s, p in violations:
        print(f"    {BLOCKED[s]}: {p}")
    print("""
raw/ 는 불변 원자료다. 추가는 되지만 수정·삭제·이름변경은 안 된다.
경로가 곧 인용 키이고, 파생 문서 수백 개가 frontmatter `source:` 로
그 경로를 가리키고 있다.

  · 매니페스트(.manifest.md)  → 수정은 허용된다. 여기 걸렸다면 삭제·이름변경이다
  · 내용이 틀렸다면      → raw 는 두고 wiki 쪽에 정정을 남긴다
  · 원본이 갱신됐다면    → 새 파일로 추가하고 매니페스트에 관계를 적는다
  · 정말 손대야 한다면   → 사유를 문서에 남기고
                            ALLOW_RAW_MUTATION=1 git commit ...
""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
