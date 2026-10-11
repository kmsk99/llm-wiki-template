---
name: verify
description: "문서와 출처를 대조하고 사용자의 명시적 확인 후 사람 확인 표시를 기록한다."
---

# Verify: 사람 확인

## 공통 실행 규칙

먼저 SCHEMA.md와 (있으면) PROJECT.md를 읽는다. Graphify는 선택 확장이며
미설정 시 색인·파일 검색으로 진행한다. 아래의 그래프 재빌드·탐색 단계는
Graphify를 활성화한 프로젝트에만 적용된다.
wiki 쓰기 전 `.venv/bin/python scripts/lint_gate.py save /tmp/wiki-before.json`,
쓰기 후 `.venv/bin/python scripts/lint_gate.py check /tmp/wiki-before.json`을 실행한다.
Windows에서는 `.venv/Scripts/python.exe`를 사용한다. 기준점 파일명은 작업별로 구분한다.
`verified: true`는 해당 문서에 대한 사용자의 명시적 확인 후 verify 절차로만 기록한다.
본문의 의미가 바뀌면 기존 verified를 false로 되돌린다. 원자료 수정 대신 새 원자료를 추가한다.

$ARGUMENTS의 문서를 읽고 source와 본문 주장을 대조한다. 인자가 없으면 대상을 묻는다.
SCHEMA.md와 PROJECT.md를 먼저 읽는다. confidence는 근거 강도이며 사람 확인과 다르다.

1. lint 기준점을 저장하고 대상과 출처를 읽는다. 출처 존재만으로 내용이 검증됐다고 보지 않는다.
2. 핵심 주장, 근거, 반대해석, 데이터 공백, 문서 간 모순을 짧게 제시한다.
3. 사용자가 해당 문서를 확인했다고 명시적으로 응답한 뒤에만 `verified: true`,
   `verified_by: <실제 확인자>`, `verified_at: <확인일 YYYY-MM-DD>`를 기록한다.
   기존 대화에 해당 문서에 대한 명시 확인이 있으면 재질문하지 않는다.
4. 승인 전에는 verified를 올리지 않는다. 에이전트 이름을 사람 확인자로 쓰지 않는다.
5. 충돌은 양쪽에 disputed와 상호 링크로 남긴다. 어느 주장이 맞는지는 임의로 확정하지 않는다.
6. lint 회귀 검사 후 확인된 범위와 남은 한계를 보고한다.

본문의 의미가 바뀌면 기존 사람 확인은 `verified: false`로 되돌리고 다시 확인받는다.
검사기가 검증하는 것은 필드 형식이며, 사람 승인 자체는 대화에서 확인해야 한다.
