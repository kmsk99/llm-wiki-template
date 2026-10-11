# AGENTS.md

<!-- llm-wiki-template:core:start -->
## 공통 운영 규칙

SCHEMA.md는 공통 정본, PROJECT.md는 사용자별 설정이다. 업데이트 전에 두 파일을 읽는다.
원자료는 추가만 허용하고 .manifest.md의 내용 갱신만 예외로 한다. 기존 parsed 파일도 덮어쓰지 않고 새 버전으로 저장한다.
12개 운영 스킬의 정본은 .claude/commands이며 .agents/skills는 생성된 프로젝트 로컬 사본이다.
Claude Code는 정본, Codex·OMP는 사본을 읽는다. 변경 후 scripts/sync_codex_skills.py를 실행한다.
wiki 수정 전후 scripts/lint_gate.py의 save/check로 새 오류를 검사한다.
confidence는 근거 강도, verified는 사람 확인이다. 명시적 확인 없이 verified를 true로 쓰지 않는다.
Graphify·파서는 선택 확장이다. 기본 설치는 python3 scripts/setup_core.py이며 그래프가 없어도 작업한다.
<!-- llm-wiki-template:core:end -->

프로젝트 목적·담당자·배치 규칙은 PROJECT.example.md를 참고해 PROJECT.md에 적는다.
