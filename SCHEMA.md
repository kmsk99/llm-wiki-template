# LLM Wiki 공통 운영 규약

이 파일은 템플릿이 관리한다. 프로젝트별 목적·담당자·배치 규칙·선택 도구는
`PROJECT.md`에 두며 업데이터는 그 파일을 교체하지 않는다. 공통 무결성 규칙을
완화할 때에는 사용자의 명시적 결정과 사유를 남긴다.

## 계층과 출처

- `raw/`: 불변 원자료. 추가만 허용한다. `.manifest.md`의 내용 수정은 장부 갱신으로 허용하되 삭제·이동은 금지한다.
- `wiki/`: 출처를 남긴 정제 지식. 결정·절차·설명을 각각 분리한다.
- `output/`: wiki에서 파생한 결과물. 새 사실을 만들지 않는다.
- `graphify-out/`: 선택적인 검색용 투영. 직접 편집하지 않는다.

잘못된 원자료는 wiki에서 정정하고, 원본의 새 버전은 새 파일로 추가한다.
파싱 결과도 raw에 등록된 뒤에는 같은 원칙을 적용한다. 신규 raw는 manifest에
기록하며 상태는 `미정`, `부분`, `완료`, `보류` 중 하나다.

## 문서 형식

정제 문서는 YAML frontmatter를 갖는다.

```yaml
---
title: 문서 제목
owner: knowledge-system
status: draft
updated: 2026-10-12
tags: []
source: [raw/example.md]
confidence: unverified
verified: false
---
```

필수 필드는 title, owner, status, updated, tags, source다. status는
`draft`, `published`, `archived` 중 하나다. source는 저장소 루트 기준 경로 또는
명시적 외부 URL 목록이며 본문에도 근거 링크를 둔다. 색인 등 source가 없는
문서는 빈 목록과 이유를 본문에 남긴다. 근거 없는 내용은 TODO·Assumption으로 표시한다.

기본 위치는 wiki/decisions, playbooks, systems, processes, projects, entities,
glossary, index, _meta다. 프로젝트별 구조는 PROJECT.md로 확장할 수 있다.
문서 추가·이동 후 wiki/index.md와 관련 색인을 갱신하고, 모순은
wiki/_meta/contradictions.md에 양쪽 근거를 남긴다.

## 근거 강도와 사람 확인

`confidence`는 에이전트가 평가하는 근거 강도(high/medium/low/unverified)다.
`verified`는 사람이 해당 문서를 읽고 명시적으로 확인했다는 별도 표시다.

- score는 confidence만 평가한다. high는 사람 검증을 의미하지 않는다.
- verify는 주장·근거·반대해석·공백을 제시하고 사람의 명시 확인 후에만
  verified: true, verified_by, verified_at을 기록한다.
- 의미가 바뀐 본문은 verified: false로 되돌려 재확인한다.
- disputed: true로 모순을 표시하고 서로 링크한다. 에이전트가 임의로 해소하지 않는다.
- lint는 형식만 확인한다. 사람의 실제 승인이나 사실의 진위를 자동 보증하지 않는다.

## 기본 작업과 검사

정본 스킬은 `.claude/commands/`다. Codex·OMP용 `.agents/skills/`는 실파일
사본으로 생성한다. 사용자 스킬은 별도 이름으로 추가하며 동기화 도구는 자신이
관리하지 않는 사본을 덮어쓰지 않는다.

| 작업 | 스킬 |
| --- | --- |
| 원자료 등록 → 위키 승격 | catalog → ingest |
| 정보 변경·근거 강도·사람 확인 | supersede · score · verify |
| 검색·출처 확인 | query · trace-citation |
| 파생 문서·기존 실행 항목 | generate · extract-actions |
| 구조·종합 점검·색인 | lint · audit · reindex |

```sh
.venv/bin/python scripts/lint_wiki.py --check
.venv/bin/python scripts/lint_gate.py save /tmp/wiki-before.json
# wiki 편집
.venv/bin/python scripts/lint_gate.py check /tmp/wiki-before.json
.venv/bin/python scripts/sync_codex_skills.py --check
```

Windows는 `.venv/Scripts/python.exe`를 사용한다. 회귀 기준점은 작업별 파일로
저장한다. lint는 필수 메타데이터, source 실재, 로컬 Markdown·위키 링크,
사람 확인 필드의 형식을 검사한다. 외부 URL의 응답·본문 진위는 별도 확인한다.
기존 오류가 있어도 이번 작업에서 추가한 오류는 회귀 게이트가 실패시킨다.

커밋 훅은 staged raw 수정·삭제·유형 변경과 알려진 시크릿 패턴을 검사한다.
값 자체는 로그에 출력하지 않는다. 모든 비밀을 탐지하는 도구는 아니며,
검토 없이 비밀을 커밋해도 된다는 뜻이 아니다. 훅 설치는 clone마다 필요하다.
기존 사용자 훅은 자동 덮어쓰지 않으며, scripts/hooks/pre-commit을 연결한다.

## 선택 확장

기본 설치에는 Graphify·LLM·문서 파서가 필요하지 않다. Graphify를 선택한
프로젝트는 관계 탐색에 그래프를 먼저 쓰고, 결과를 실제 문서와 대조한다.
노드 라벨 부분 문자열 검색은 동의어 의미 검색이 아니다. 그래프가 없거나
오래됐으면 색인·파일 검색으로 보완하고 한계를 밝힌다. 재빌드는 명시적으로
활성화한 provider 설정을 사용하며 임의의 유료 provider로 전환하지 않는다.
파서·Graphify 전체 설치와 세부 명령은 GUIDE.md를 참고한다.
