---
name: extract-actions
description: "Wiki에 흩어진 TODO, Open question, FIXME 등 미해결 마커를 탐지·수집한다."
---

# Extract Actions: 실행 항목 탐지 및 수집

## 공통 실행 규칙

먼저 SCHEMA.md와 (있으면) PROJECT.md를 읽는다. Graphify는 선택 확장이며
미설정 시 색인·파일 검색으로 진행한다. 아래의 그래프 재빌드·탐색 단계는
Graphify를 활성화한 프로젝트에만 적용된다.
wiki 쓰기 전 `.venv/bin/python scripts/lint_gate.py save /tmp/wiki-before.json`,
쓰기 후 `.venv/bin/python scripts/lint_gate.py check /tmp/wiki-before.json`을 실행한다.
Windows에서는 `.venv/Scripts/python.exe`를 사용한다. 기준점 파일명은 작업별로 구분한다.
`verified: true`는 해당 문서에 대한 사용자의 명시적 확인 후 verify 절차로만 기록한다.
본문의 의미가 바뀌면 기존 verified를 false로 되돌린다. 원자료 수정 대신 새 원자료를 추가한다.

wiki 문서에 이미 존재하는 미해결 마커(TODO, Open question, FIXME 등)를 **스캔하여 수집**한다.
`/project:generate actions`와의 차이: generate는 wiki 지식을 종합하여 새로운 실행 항목을 도출하는 반면, extract-actions는 기존 문서에 흩어진 마커를 모아 정리한다.

## 입력

$ARGUMENTS

- 인자가 없으면: 최근 7일간 갱신된 wiki 문서에서 추출한다.
- 파일/디렉토리가 주어지면: 해당 범위에서만 추출한다.
- `--all`이 붙으면: wiki 전체에서 추출한다.

## 추출 대상

다음 패턴에서 실행 항목을 식별한다:

1. **TODO 마커**: `TODO`, `FIXME`, `ACTION`이 포함된 줄
2. **Open question**: 답변이 필요한 미해결 질문
3. **결정 사항의 후속 조치**: wiki/decisions/ 문서의 `## Next steps` 또는 `## 후속 조치`
4. **playbook 갱신 필요**: 프로세스 변경으로 playbook이 outdated된 경우
5. **모순 해소**: wiki/_meta/contradictions.md의 미해결 항목

## 실행 절차

1. 대상 wiki 문서를 스캔한다.
2. 위 5가지 패턴에서 실행 항목을 추출한다.
3. 각 항목에 다음을 부여한다:
   - **우선순위**: P0(긴급), P1(중요), P2(개선)
   - **유형**: `investigate` | `update-wiki` | `resolve-contradiction` | `create-doc` | `verify`
   - **출처**: 해당 wiki 문서 경로
4. 기존 `output/action-items/` 문서와 중복을 확인한다.
5. 새 액션 아이템 문서를 생성하거나 기존 문서에 추가한다.

## 출력

```
## Action Items — {날짜}

### P0 — 긴급
| # | 항목 | 유형 | 출처 |
|---|------|------|------|

### P1 — 중요
| # | 항목 | 유형 | 출처 |
|---|------|------|------|

### P2 — 개선
| # | 항목 | 유형 | 출처 |
|---|------|------|------|

### 통계
- 총 N개 항목 추출
- 신규: N개 / 기존 대비 변경: N개
```

## 규칙
- 추출만 한다. 직접 해결하지 않는다.
- 모든 항목에 출처를 명시한다.
- 이미 완료된 항목(체크된 TODO 등)은 제외한다.
