# Audit: 위키 전체 건강 상태 점검

`/project:lint`보다 포괄적인 전체 위키 감사. 구조적 문제뿐 아니라 지식의 완전성과 품질까지 평가한다.
lint가 구조적 문제에 집중한다면, audit은 커버리지, 신뢰도, 최신성, 연결성까지 종합 점검한다.
월 1회 또는 위키가 크게 변동된 후 실행을 권장한다.

## 입력

$ARGUMENTS

- 인자가 없으면: 전체 감사를 수행한다.
- `--quick`이 붙으면: 핵심 지표만 빠르게 점검한다.

## 감사 영역

### 1. 구조 감사 (lint 포함)
- lint의 모든 항목을 수행한다 (고아, 깨진 링크, frontmatter, 모순, 구조 위반, 색인).
- 추가로 디렉토리 구조가 CLAUDE.md의 명세와 일치하는지 확인한다.

### 2. 커버리지 감사
- raw/.manifest.md의 전체 소스 대비 ingested 비율을 계산한다.
- 각 wiki 하위 디렉토리(systems, processes, projects, decisions, playbooks, entities, glossary)의 문서 수를 집계한다.
- 비어있는 디렉토리를 보고한다.

### 3. 신뢰도 감사
- score 스킬의 기준으로 전체 문서의 confidence 분포를 점검한다.
- `confidence:` 필드가 없는 문서를 나열한다.
- 🔴 Unverified 문서의 비율이 20%를 넘으면 경고한다.

### 4. 최신성 감사
- `updated:` 날짜 기준으로 문서 노후도 분포를 계산한다:
  - 7일 이내: 🟢 Fresh
  - 30일 이내: 🟡 Current
  - 90일 이내: 🟠 Aging
  - 90일 초과: 🔴 Stale
- 🔴 Stale 문서는 archive 후보로 표시한다.

### 5. 연결성 감사 (Graphify 지표 기반)
- **우선 원천은 `graphify-out/GRAPH_REPORT.md`와 `graph.json`**이다. 그래프가 stale이면 `graphify . --update` 후 진행한다.
- 수집할 정량 지표:
  - 총 노드 수 · 엣지 수 · 커뮤니티 수
  - 평균 엣지 수/노드 (목표: ≥ 2.0)
  - 고립 노드 비율 (엣지 0~1): 10% 초과 시 🔴
  - God Nodes Top 10 (가장 참조되는 허브)
  - Low-cohesion 커뮤니티 (cohesion < 0.1): 문서 군이 느슨하게 묶여 있다는 신호
  - Surprising connections: 리뷰가 필요한 AMBIGUOUS 엣지
- 파일 링크 밀도(문서당 markdown 링크 수)는 보조 지표로 유지한다.

### 6. Output 정합성
- output/ 문서가 참조하는 wiki 페이지가 모두 존재하는지 확인한다.
- output이 wiki에 없는 사실을 포함하고 있지 않은지 샘플 검사한다.

## 출력

```
## Wiki Audit Report — {날짜}

### Executive Summary
- 전체 건강도: {🟢|🟡|🟠|🔴} ({점수}/100)
- 총 문서 수: N (wiki: N, output: N)
- Raw 소스 커버리지: N/M ({비율}%)

### 구조
- Lint 결과: 🔴 N errors, ⚠️ N warnings

### 커버리지
| 영역 | 문서 수 | 상태 |
|------|---------|------|

### 신뢰도 분포
| 등급 | 문서 수 | 비율 |
|------|---------|------|

### 최신성 분포
| 상태 | 문서 수 | 비율 |
|------|---------|------|

### 연결성
- 평균 cross-link: N개/문서
- 고립 문서: N개
- 허브 문서 Top 5: ...

### 권장 조치 (우선순위순)
1. ...
2. ...
3. ...
```

## 규칙
- audit은 읽기 전용이다. 문서를 수정하지 않는다.
- 구체적이고 실행 가능한 권장 조치를 제시한다.
- 점수는 6개 영역의 가중 평균으로 산출한다.
