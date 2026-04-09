---
name: generate
description: "Wiki 지식을 기반으로 브리프, 온보딩, 리포트, 액션 아이템 등 output 문서를 생성한다."
---

# Generate: Wiki → Output 파생 문서 생성

wiki/에 축적된 지식을 기반으로 output/ 디렉토리에 행동 지향 문서를 생성한다.

## 입력

$ARGUMENTS

형식: `<유형> [주제/범위]`

유형:
- `brief` — 의사결정 브리프, 인사이트 요약 → `output/briefs/`
- `onboarding` — 신규 입사자 온보딩 가이드 → `output/onboarding/`
- `actions` — wiki 지식을 종합하여 실행 항목 도출 → `output/action-items/` (기존 마커 수집은 `/project:extract-actions` 사용)
- `report` — 주간/월간 리포트 → `output/reports/`

예시:
- `brief 사장링크 현황` → 사장링크에 대한 의사결정 브리프
- `onboarding 데이터팀` → 데이터팀 신규 입사자용 가이드
- `actions 2026-04주차` → 이번 주 액션 아이템
- `report weekly` → 주간 위키 변경 리포트

## 실행 절차

### Phase 1: 소스 수집
1. 주제/범위에 해당하는 wiki 문서를 모두 찾는다.
2. 관련 wiki/decisions/, wiki/playbooks/ 문서도 포함한다.
3. 최근 변경된 문서를 우선 고려한다 (git log 활용).

### Phase 2: 생성

#### Brief
```markdown
---
title: {주제} 브리프
type: brief
generated: {오늘 날짜}
source: [wiki 페이지 목록]
---

## 핵심 요약
(3~5문장)

## 현재 상태

## 주요 사실

## 열린 질문

## 권장 행동
```

#### Onboarding
```markdown
---
title: {팀/역할} 온보딩 가이드
type: onboarding
generated: {오늘 날짜}
source: [wiki 페이지 목록]
---

## 먼저 읽을 문서
(순서대로)

## 핵심 시스템 이해

## 주요 프로세스

## 자주 쓰는 용어

## 누구에게 물어볼까
```

#### Actions
```markdown
---
title: {범위} 실행 항목
type: action-items
generated: {오늘 날짜}
source: [wiki 페이지 목록]
---

## 실행 항목
| # | 항목 | 근거 | 우선순위 | 담당 |
|---|------|------|----------|------|
```

#### Report
```markdown
---
title: {기간} 위키 리포트
type: report
generated: {오늘 날짜}
source: [wiki 페이지 목록]
---

## 기간 요약

## 새로 추가된 지식

## 갱신된 문서

## 해소된 모순

## 남은 과제
```

### Phase 3: 검증
4. output에 wiki에 없는 새로운 사실이 포함되지 않았는지 확인한다.
5. 모든 사실에 wiki 출처를 명시한다.

### Phase 4: 보고
6. 생성된 파일 경로와 사용된 wiki 소스 목록을 출력한다.

## 규칙
- **output/에서 wiki에 없는 새로운 사실을 만들지 않는다.** 이것이 가장 중요한 규칙이다.
- 모든 output 문서의 frontmatter `source:`에 기반 wiki 페이지를 명시한다.
- 기존 output 문서가 있으면 갱신한다 (중복 생성 방지).
- 생성 과정에서 wiki 갭을 발견하면 보고하되, output에서 채우지 않는다.
