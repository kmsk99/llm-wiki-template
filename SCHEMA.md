# SCHEMA.md — LLM Wiki 동작 명세

이 문서는 LLM 에이전트가 이 위키를 운영할 때 따라야 하는 **모든 동작(Operation)**을 정의한다.
Karpathy LLM Wiki 패턴의 핵심 3가지(Ingest, Query, Lint)를 기반으로,
실제 운영에 필요한 세부 동작까지 체계적으로 명세한다.

2026-04-18부로 **Graphify 지식 그래프**가 위키 운영의 1차 탐색·검증 계층으로 통합되었다.
이 파일은 파일 시스템 관점(raw/wiki/output)과 그래프 관점(graphify-out/)을 **하나의 운영 규약**으로 묶는다.

> **이 파일은 규칙이다.** 에이전트는 아래 동작을 수행할 때 반드시 이 명세를 따른다.
> 구체적인 절차는 `.claude/commands/` (Claude Code) / `.agents/skills/` (Codex CLI)의 각 스킬 파일에 정의되어 있다.

---

## 아키텍처 개요

```
                      ┌──────────────────────────────────────┐
                      │          READ-ONLY OVERLAY            │
                      │         graphify-out/                 │
                      │   GRAPH_REPORT.md · graph.json ·      │
                      │   커뮤니티 허브 · god node 인덱스     │
                      └──────────▲───────────────▲────────────┘
                                 │ rebuild        │ query/path/explain
                                 │ (Write 종료 시)│ (Read 시작 시)
                                 │                │
raw/  ──→  Ingest  ──→  wiki/  ──→  Generate  ──→  output/
 │        Supersede        ↕ ↕
 Catalog                Lint · Score
 Parse               Reindex · Cross-link · Query
                     ←── Trace Citation ──→
                     ←────── Audit ────────→
```

**3개 층의 역할 분리**

| 층 | 성격 | 수정 권한 |
|---|---|---|
| `raw/` | 불변 원자료 | 읽기 전용 (추가만 가능) |
| `wiki/` | LLM이 정제한 지식 (진실의 현재 상태) | Write 스킬로만 수정 |
| `graphify-out/` | wiki를 투영한 지식 그래프 | **직접 편집 금지, 재생성만** |
| `output/` | wiki에서 파생된 행동 산출물 | Generate 스킬로만 생성 |

---

## Graphify Layer — 1차 탐색 계층

### 무엇인가

`graphify-out/`는 wiki/를 입력으로 생성된 **재생 가능한 지식 그래프**다.
- `GRAPH_REPORT.md` — god node·커뮤니티 허브·hyperedge·surprising connection 요약.
- `graph.json` — 노드·엣지 원본 데이터 (탐색 쿼리의 백엔드).
- `chunks/`, `cache/`, `manifest.json` — 증분 빌드를 위한 캐시.

### 왜 필요한가

| 기존 SCHEMA의 한계 | Graphify가 보완하는 것 |
|---|---|
| Query Phase 1이 Grep 기반 → 동의어/우회 표현 누락 | 개념 노드·커뮤니티로 **의미적 근접** 문서 발견 |
| Lint의 고아 페이지 탐지가 휴리스틱 | 그래프 구조로 **구조적 고립** 자동 식별 |
| Audit의 연결성 평가가 주관적 | 노드 수·엣지 수·커뮤니티 수 **정량 지표** |
| Reindex가 수동 index만 갱신 | god node 순위로 **index 후보 자동 추천** |
| Trace Citation이 단일 hop 링크만 추적 | `graphify path`로 **다단 경로** 추적 |
| Generate 시 목차를 매번 재고민 | 커뮤니티 허브를 **목차 골격**으로 재사용 |

### 사용 방법

```bash
# Claude Code 내부
/graphify query "질문"          # 의미 기반 검색
/graphify path "A" "B"           # 두 개념 사이 경로
/graphify explain "개념"         # 특정 노드·이웃 설명
/graphify . --update             # wiki 변경 후 증분 재빌드

# 터미널
graphify query "질문"
graphify path "A" "B"
graphify . --update
```

### 재빌드 트리거 (중요)

다음 동작이 끝나면 **반드시** `graphify . --update`를 호출한다:

- `/project:ingest` 완료 후
- `/project:supersede` 완료 후
- `/project:reindex` 완료 후
- `wiki/` 수동 편집으로 5개 이상 문서가 바뀐 후

재빌드를 건너뛰면 **Read 스킬이 stale 그래프를 근거로 잘못된 답을 생성**한다. 이것이 가장 흔한 장애 원인이다.

---

## 동작 카탈로그

각 스킬에 **Graphify 연동 역할**을 명시한다.

### Tier 1 — 기본 루프

| 동작 | 스킬 | 설명 | Graphify 역할 |
|------|------|------|----------------|
| **Ingest** | `/project:ingest` | raw → wiki 승격 | Phase 끝에 그래프 재빌드, 신규 문서의 god node 편입 여부 보고 |
| **Lint** | `/project:lint` | 위키 건강검진 | 그래프 기반 고아 노드·low-cohesion 커뮤니티 탐지 |

**Ingest의 하위 동작:**
- **Read/Parse**: 비텍스트 파일 하이브리드 파싱 (`scripts/parse-raw.sh`)
- **Create/Update Page**: 템플릿 기반 작성
- **Cross-link**: 양방향 링크 생성 (커뮤니티 내 god node와 우선 링크)
- **Reindex + Graph Rebuild**: `wiki/index.md` 갱신 + `graphify . --update`

### Tier 2 — 품질 유지

| 동작 | 스킬 | 설명 | Graphify 역할 |
|------|------|------|----------------|
| **Supersede** | `/project:supersede` | 정보 대체 + Change log | 파급 영향 문서 탐색에 `graphify path` 활용, 종료 시 재빌드 |
| **Score** | `/project:score` | 신뢰도 평가 | (직접 연동 없음) |

### Tier 3 — 가치 창출

| 동작 | 스킬 | 설명 | Graphify 역할 |
|------|------|------|----------------|
| **Query** | `/project:query` | 질문 → 답변 → 위키 강화 | **Phase 1 검색은 graphify 우선** (query/path/explain), Grep은 정확 매칭 보조 |
| **Generate** | `/project:generate` | wiki → output 파생 | 커뮤니티 허브를 목차 골격으로, god node 중심으로 소스 수집 |
| **Extract Actions** | `/project:extract-actions` | TODO/Open question 수집 | (직접 연동 없음) |

### Tier 4 — 스케일링

| 동작 | 스킬 | 설명 | Graphify 역할 |
|------|------|------|----------------|
| **Audit** | `/project:audit` | 종합 감사 | 연결성 영역에서 그래프 지표(노드·엣지·커뮤니티·고립률) 1차 입력 |
| **Catalog** | `/project:catalog` | raw 등록 + 파싱 | (wiki를 건드리지 않으므로 재빌드 불필요) |
| **Reindex** | `/project:reindex` | 색인 재구축 | 완료 후 그래프 재빌드, god node 순위를 index 후보로 활용 |
| **Trace Citation** | `/project:trace-citation` | 근거 역추적 | `graphify path <사실> <raw 소스>`로 경로 후보 탐색, 파일로 최종 검증 |

---

## 동작 간 관계

### 쓰기 흐름 (Write Path)

```
새 소스 도착
    │
    ▼
  Catalog  ──→  raw/.manifest.md 등록 + 비텍스트 파싱
    │
    ▼
  Ingest   ──→  wiki 문서 생성/갱신 + Cross-link + Reindex
    │
    ├──→  모순 발견 시 → contradictions.md 기록
    │
    ▼
  [Graph Rebuild]  ──→  graphify . --update   ★필수
    │
    ▼
  Score    ──→  신뢰도 평가
    │
    ▼
  Generate ──→  output 문서 생성 (그래프 커뮤니티를 목차로)
```

### 변경 흐름 (Supersede Path)

```
정보 변경 감지
    │
    ▼
  Supersede ──→  기존 문서 갱신 + Change log + 파급 효과 추적
    │               (파급 탐색에 `graphify path` 활용)
    ▼
  [Graph Rebuild]  ──→  graphify . --update   ★필수
```

### 주기적 점검

```
주 1회
    │
    ├──→  Lint       ──→  구조 + 그래프 고립 노드 탐지/수정
    ├──→  Score      ──→  신뢰도 재평가
    ├──→  Reindex    ──→  색인 정합성 + 그래프 재빌드
    └──→  Extract Actions ──→  실행 항목 정리
```

```
월 1회
    │
    └──→  Audit      ──→  구조 + 커버리지 + 신뢰도 + 최신성 + 그래프 연결성
```

### 질의 흐름 (Read Path)

```
사용자 질문
    │
    ▼
  Graphify  ──→  GRAPH_REPORT.md 훑기 · query/explain으로 관련 노드 수집
    │               (그래프 stale이면 먼저 `graphify . --update`)
    ▼
  wiki 파일 읽기  ──→  Graphify가 지목한 문서를 실제로 읽어 답변 구성
    │
    ▼
  Grep/Glob  ──→  인용 문구·정확한 숫자 확인용 보조 검색만
    │
    ▼
  Query 스킬이 통찰 발견 시 → wiki 갱신 → (Write Path로 복귀)
```

---

## 운영 규칙 (모든 동작에 적용)

### Manifest 인제스트 상태
`raw/.manifest.md`에서 사용하는 상태값은 다음 4가지만 허용한다:
- **완료**: wiki/ 문서로 승격 완료
- **미정**: 아직 인제스트하지 않음
- **부분**: 일부만 승격, 추가 작업 필요
- **보류**: 의도적으로 보류 (사유를 비고에 기록)

### 불변 규칙

**원본·출처**
1. **근거 없이 쓰지 않는다.** 불확실하면 `TODO`, `Open question`, `Assumption`으로 남긴다.
2. **raw/는 절대 수정하지 않는다.** 읽기 전용.
3. **출처를 항상 남긴다.** frontmatter `source:`와 본문 링크.

**구조·색인**
4. **관심사를 분리한다.** decisions/, playbooks/, systems/ 등을 혼합하지 않는다.
5. **색인을 갱신한다.** 문서 추가/이동 시 wiki/index.md와 관련 맵 갱신.
6. **모순을 추적한다.** 발견 즉시 wiki/_meta/contradictions.md에 기록.
7. **manifest를 갱신한다.** raw 소스 추가 시 raw/.manifest.md 갱신.

**Graphify 계층**
8. **graphify-out/는 파생물이다.** 직접 편집하지 않고, wiki 변경 후 `graphify . --update`로 재생성한다.
9. **Write 스킬은 종료 시 그래프를 재빌드한다.** Ingest · Supersede · Reindex · 5개 이상 문서 수동 편집 후 필수.
10. **Read 스킬은 Graphify를 1차 입력으로 삼는다.** 주제·구조·관계 탐색은 graphify query/path/explain 먼저, Grep은 정확 매칭에만 사용.
11. **Stale 그래프에 근거해 답하지 않는다.** `GRAPH_REPORT.md`의 타임스탬프가 마지막 wiki 변경보다 오래되면 재빌드 후 질의한다.

**output/ 특별 규칙**
12. **output에서 새 사실을 만들지 않는다.** wiki에 있는 내용만 파생.
13. **output의 모든 사실에 wiki 출처를 명시한다.**

### 자동화 권장

- **Catalog + Ingest + Graph Rebuild**: 새 파일 감지 시 자동 실행 (파일 워처 또는 cron)
- **Lint + Reindex + Graph Rebuild**: 주 1회 자동 실행
- **Audit (그래프 지표 포함)**: 월 1회 자동 실행
- **나머지**: 대화형으로 에이전트에게 요청

---

## Graphify vs Grep/Glob 사용 기준 (Hard Rule)

| 상황 | 도구 | 이유 |
|------|------|------|
| 주제·관계·구조·커뮤니티·출처 흐름 탐색 | **Graphify** (`/graphify query|path|explain`, `GRAPH_REPORT.md`) | 개념 관계·커뮤니티까지 함께 제공 |
| 동의어·유사 개념·의미적 근접 검색 | **Graphify** | Grep은 문자열 일치만 가능 |
| 그래프 부재/오래됨 | `graphify . --update` / `/graphify <path>` | 현재 코퍼스 기준 재빌드 |
| 정확한 파일명·경로 | **Glob** | 파일시스템 정확 매칭 |
| 정확한 문자열·정규식·숫자 인용 | **Grep** | 패턴 정확도 |
| 코드/설정/스크립트 파일(.sh/.json/.yml) | **Grep/Glob** | 그래프화 대상이 아님 |

**원칙**: 의미는 Graphify로, 문자는 Grep/Glob으로.

---

## 스킬 호출 예시

```bash
# 새 raw 소스 등록 + 인제스트 (재빌드 자동)
/project:catalog raw/meetings/2026-04-09-standup.md
/project:ingest raw/meetings/2026-04-09-standup.md

# 미등록 raw 소스 일괄 등록
/project:catalog

# 위키에 질문 (Graphify 우선 탐색)
/project:query 서비스 아키텍처는?

# 건강검진
/project:lint
/project:lint --fix

# 종합 감사 (그래프 연결성 포함)
/project:audit

# 브리프 생성 (커뮤니티 허브 기반 목차)
/project:generate brief 서비스 현황

# 정보 대체 (파급 탐색에 graphify path 사용)
/project:supersede raw/meetings/2026-04-09-pricing.md wiki/decisions/pricing-v2.md

# 출처 추적 (그래프 경로 + 파일 검증)
/project:trace-citation wiki/systems/my-system.md

# 색인 + 그래프 재구축
/project:reindex

# 수동 그래프 재빌드 (대량 편집 후)
graphify . --update
```

---

## 스킬 자동 사용 가이드

### Claude Code

이 레포의 `.claude/commands/` 디렉토리에 있는 스킬들은 Claude Code의 **slash command**로 자동 등록된다.

```bash
> /project:ingest raw/meetings/2026-04-09-standup.md
> /project:query 서비스 아키텍처는?
> /project:lint --fix
```

### Codex CLI

같은 스킬이 `.agents/skills/<name>/SKILL.md`에 미러링되어 있다. `$<스킬명>`으로 호출한다.

### 자연어 트리거

| 자연어 요청 | 자동 선택 스킬 |
|-------------|---------------|
| "새 회의록 올렸어, 위키에 반영해줘" | `/project:catalog` → `/project:ingest` |
| "위키 상태 좀 점검해줘" | `/project:lint` |
| "이 시스템이 뭐야?" | `/project:query` |
| "이번 주 액션 아이템 정리해줘" | `/project:extract-actions` |
| "온보딩 가이드 만들어줘" | `/project:generate onboarding` |
| "가격이 바뀌었어" | `/project:supersede` |
| "이 문서 근거가 맞아?" | `/project:trace-citation` |
| "위키 전체 감사해줘" | `/project:audit` |
| "두 개념이 어떻게 연결돼?" | `/graphify path` |
| "이 주제 주변에 뭐가 있어?" | `/graphify explain` |

### 권장 워크플로우

#### 일상 (새 소스 추가 시)
```
1. raw/에 파일 저장
2. /project:catalog          ← 소스 등록 + 비텍스트 파싱
3. /project:ingest           ← wiki로 승격 (자동 재빌드 포함)
```

#### 주간
```
1. /project:lint --fix       ← 구조 + 그래프 고립 노드 점검
2. /project:reindex          ← 색인 + 그래프 재구축
3. /project:extract-actions  ← 미해결 항목 수집
```

#### 월간
```
1. /project:audit            ← 종합 건강도 (그래프 연결성 포함)
2. /project:score            ← 신뢰도 재평가
3. /project:generate report weekly  ← 리포트 생성
```

#### 수시
```
/project:query <질문>           ← Graphify 우선 검색 후 답변
/project:supersede <소스>       ← 정보 변경 + 파급 효과 그래프 추적
/project:trace-citation <문서>  ← 그래프 경로 + 파일 검증
/graphify query|path|explain    ← 직접 그래프 탐색
```
