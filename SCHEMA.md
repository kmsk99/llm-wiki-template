# SCHEMA.md — LLM Wiki 동작 명세

이 문서는 LLM 에이전트가 이 위키를 운영할 때 따라야 하는 **모든 동작(Operation)**을 정의한다.
Karpathy LLM Wiki 패턴의 핵심 3가지(Ingest, Query, Lint)를 기반으로,
실제 운영에 필요한 세부 동작까지 체계적으로 명세한다.

> **이 파일은 규칙이다.** 에이전트는 아래 동작을 수행할 때 반드시 이 명세를 따른다.
> 구체적인 절차는 `.claude/commands/` 디렉토리의 각 스킬 파일에 정의되어 있다.

---

## 아키텍처 개요

```
raw/  ──→  Ingest  ──→  wiki/  ──→  Generate  ──→  output/
 │                        ↕ ↕                         │
 Catalog              Lint · Score                    │
 Parse              Supersede · Reindex               │
                    Cross-link · Query          Extract Actions
                                                  Report
                    ←── Trace Citation ──→
                    ←────── Audit ────────→
```

## 동작 카탈로그

### Tier 1 — 기본 루프 (이것 없이는 시작 불가)

| 동작 | 스킬 | 설명 |
|------|------|------|
| **Ingest** | `/project:ingest` | raw → wiki 승격. 소스 읽기 → 분석 → 문서 생성/갱신 → 색인 갱신 → 보고 |
| **Lint** | `/project:lint` | 위키 건강검진. 고아 페이지, 깨진 링크, frontmatter 누락, 모순, 구조 위반, 지식 공백 탐지 |

**Ingest의 하위 동작:**
- **Read/Parse**: 소스 읽기. 비텍스트 파일은 파싱 (`scripts/parse-raw.sh`, PDF → pdftotext, 그 외 → MarkItDown)
- **Create/Update Page**: 템플릿 기반 문서 생성 또는 기존 문서 갱신
- **Cross-link**: 관련 문서 간 양방향 링크 생성
- **Reindex**: `wiki/index.md`와 주제별 맵 갱신 (`/project:reindex`)

### Tier 2 — 위키 품질 유지 (30페이지 넘으면 필수)

| 동작 | 스킬 | 설명 |
|------|------|------|
| **Supersede** | `/project:supersede` | 기존 정보가 새 정보로 대체될 때 안전하게 갱신하고 `## Change log`에 이력 보존, 파급 효과 추적 |
| **Score** | `/project:score` | 문서별 신뢰도(confidence) 평가. 소스 품질, 최신성, 교차 검증 기준 |

### Tier 3 — 가치 창출 (실제 쓸모를 만드는 동작)

| 동작 | 스킬 | 설명 |
|------|------|------|
| **Query** | `/project:query` | 질문 → 답변 → 위키 재기록 선순환. 단순 조회 시에는 wiki 수정 없이 답변만 제공 |
| **Generate** | `/project:generate` | wiki → output 파생. 브리프, 온보딩, 리포트. wiki 지식을 종합하여 새로운 실행 항목 도출 |
| **Extract Actions** | `/project:extract-actions` | wiki에 흩어진 기존 마커(TODO, Open question, FIXME)를 탐지·수집 |

### Tier 4 — 스케일링 & 횡단 동작

| 동작 | 스킬 | 설명 |
|------|------|------|
| **Audit** | `/project:audit` | lint + 커버리지 + 신뢰도 + 최신성 + 연결성 + output 정합성 종합 감사 |
| **Catalog** | `/project:catalog` | raw 소스를 manifest에 등록하고 비텍스트 파일을 파싱 |
| **Reindex** | `/project:reindex` | wiki/index.md와 주제별 맵 재구축 |
| **Trace Citation** | `/project:trace-citation` | 특정 사실의 근거를 raw 소스까지 역추적 |

---

## 동작 간 관계

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
  Score    ──→  신뢰도 평가
    │
    ▼
  Generate ──→  output 문서 생성
```

```
정보 변경 감지
    │
    ▼
  Supersede ──→  기존 문서 갱신 + 파급 효과 추적 + 모순 해소
```

```
주기적 (주 1회 권장)
    │
    ├──→  Lint       ──→  구조적 문제 탐지/수정
    ├──→  Score      ──→  신뢰도 재평가
    ├──→  Reindex    ──→  색인 정합성 확보
    └──→  Extract Actions ──→  실행 항목 정리
```

```
월 1회 또는 필요 시
    │
    └──→  Audit      ──→  종합 건강도 점검 + 권장 조치
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
1. **근거 없이 쓰지 않는다.** 불확실하면 `TODO`, `Open question`, `Assumption`으로 남긴다.
2. **raw/는 절대 수정하지 않는다.** 읽기 전용.
3. **출처를 항상 남긴다.** frontmatter `source:`와 본문 링크.
4. **관심사를 분리한다.** decisions/, playbooks/, systems/ 등을 혼합하지 않는다.
5. **색인을 갱신한다.** 문서 추가/이동 시 wiki/index.md와 관련 맵 갱신.
6. **모순을 추적한다.** 발견 즉시 wiki/_meta/contradictions.md에 기록.
7. **manifest를 갱신한다.** raw 소스 추가 시 raw/.manifest.md 갱신.

### output/ 특별 규칙
8. **output에서 새 사실을 만들지 않는다.** wiki에 있는 내용만 파생.
9. **output의 모든 사실에 wiki 출처를 명시한다.**

### 자동화 권장
- **Catalog + Ingest**: 새 파일 감지 시 자동 실행 (파일 워처 또는 cron)
- **Lint + Reindex**: 주 1회 자동 실행
- **나머지**: 대화형으로 에이전트에게 요청

---

## 스킬 호출 예시

```bash
# 새 raw 소스 등록 + 인제스트
/project:catalog raw/meetings/2026-04-09-standup.md
/project:ingest raw/meetings/2026-04-09-standup.md

# 미등록 raw 소스 일괄 등록
/project:catalog

# 위키에 질문
/project:query 서비스 아키텍처는?

# 건강검진
/project:lint
/project:lint --fix

# 종합 감사
/project:audit

# 브리프 생성
/project:generate brief 서비스 현황

# 주간 리포트
/project:generate report weekly

# 정보 대체
/project:supersede raw/meetings/2026-04-09-pricing.md wiki/decisions/pricing-v2.md

# 출처 추적
/project:trace-citation wiki/systems/my-system.md

# 액션 아이템 추출
/project:extract-actions

# 신뢰도 평가
/project:score wiki/systems/

# 색인 재구축
/project:reindex
```

---

## 스킬 자동 사용 가이드

### Claude Code에서 사용하기

이 레포의 `.claude/commands/` 디렉토리에 있는 스킬들은 Claude Code의 **slash command**로 자동 등록된다.
Claude Code 프롬프트에서 `/project:` 접두어로 바로 호출할 수 있다.

```bash
# Claude Code 프롬프트에서:
> /project:ingest raw/meetings/2026-04-09-standup.md
> /project:query 서비스 아키텍처는?
> /project:lint --fix
```

### 자연어로 사용하기

slash command를 직접 입력하지 않아도, Claude Code에게 자연어로 요청하면 적절한 스킬을 자동으로 선택한다:

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

### 권장 워크플로우

#### 일상 (새 소스 추가 시)
```
1. raw/에 파일 저장
2. /project:catalog          ← 소스 등록 + 비텍스트 파싱
3. /project:ingest           ← wiki로 승격
```

#### 주간 (주 1회)
```
1. /project:lint --fix       ← 구조 점검 + 자동 수정
2. /project:reindex          ← 색인 정합성 확보
3. /project:extract-actions  ← 미해결 항목 수집
```

#### 월간 (월 1회)
```
1. /project:audit            ← 종합 건강도 점검
2. /project:score            ← 신뢰도 재평가
3. /project:generate report weekly  ← 리포트 생성
```

#### 수시
```
/project:query <질문>        ← 위키에 질문 (답변 + 위키 강화)
/project:supersede <소스>    ← 정보 변경 반영
/project:trace-citation <문서>  ← 출처 역추적
```
