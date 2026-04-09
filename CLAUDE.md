# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
It also serves as the **SCHEMA** — the operating instructions for LLM agents managing this knowledge wiki.

## What This Repo Is

A Markdown-based knowledge wiki, structured as a Karpathy-style LLM Wiki.
It accumulates tacit knowledge and operational information as Markdown documents across three layers:
**raw** (immutable sources) → **wiki** (LLM-maintained refined knowledge) → **output** (derived action artifacts).

## Three-Layer Architecture

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

### Layer 1: raw/ — Immutable Sources
원자료 저장소. 회의록, 슬랙 발췌, 전사, 초안, 링크 덤프, PDF, Excel, PPTX 등 바이너리 파일 포함.
- **절대 수정·삭제하지 않는다** — 이것이 진실의 원천이다.
- 새 소스 추가 시 `raw/.manifest.md`를 갱신한다.
- **비텍스트 파일은 파싱 엔진으로 변환한다.**
  - PDF → Marker (`marker-pdf`, CLIProxyAPI + LLM 보정)
  - 그 외 (XLSX, DOCX, PPTX, 이미지, HTML, 오디오 등) → MarkItDown
  - `scripts/parse-raw.sh`를 실행하면 `*.parsed.md` 파일이 원본 옆에 생성된다.
  - Ingest 시 원본이 아닌 `.parsed.md`를 읽어 wiki로 승격한다.
  - LLM 없이 실행하려면 `--no-llm` 플래그를 사용한다.
  - 원본이 갱신되면 자동으로 재파싱한다.

### Layer 2: wiki/ — LLM-Maintained Knowledge
모든 정제 문서가 이 우산 아래에 있다. LLM이 Ingest/Query/Lint를 통해 유지보수한다.

### Layer 3: output/ — Derived Artifacts
wiki/에 축적된 지식에서 파생되는 행동 지향 문서. 브리프, 온보딩 가이드, 액션 아이템, 리포트 등.
- wiki에 없는 사실을 output에서 새로 만들지 않는다.

## Directory Purpose

| Directory | Contains |
|-----------|----------|
| `raw/` | 불변 원자료: 회의록, 슬랙, 전사, 초안, 링크, PDF/Excel/PPTX 등 |
| `scripts/setup.sh` | 원스톱 환경 셋업 (크로스 플랫폼: macOS, Linux, Windows) |
| `scripts/parse-raw.sh` | 비텍스트 파일 → Markdown 파싱 (Marker + MarkItDown) |
| `raw/.manifest.md` | 전체 raw 소스 목록과 인제스트 상태 추적 |
| `wiki/systems/` | 시스템 설명 |
| `wiki/processes/` | 프로세스 설명 |
| `wiki/projects/` | 프로젝트 설명 |
| `wiki/decisions/` | ADR 형식의 의사결정 기록 |
| `wiki/playbooks/` | 운영 절차, 대응 runbook |
| `wiki/entities/` | 핵심 객체: 브랜드, 고객, 파트너, 시스템 |
| `wiki/glossary/` | 사내 용어 정의 |
| `wiki/index.md` | 마스터 네비게이션 맵 |
| `wiki/index/` | 주제별 맵 |
| `wiki/_meta/` | 모순 추적, 위키 건강도 |
| `output/briefs/` | 의사결정 브리프, 인사이트 요약 |
| `output/onboarding/` | 신규 입사자 온보딩 가이드 |
| `output/action-items/` | 실행 항목 |
| `output/reports/` | 주간·월간 리포트 |
| `templates/` | 문서 템플릿 |
| `prompts/` | 재사용 에이전트 프롬프트 |
| `.claude/commands/` | 11개 위키 운영 스킬 (Claude Code slash commands) |
| `.claude/settings.json` | MCP 서버 설정 (qmd) |
| `.agents/skills/` | 11개 위키 운영 스킬 (Codex CLI skills) |
| `SCHEMA.md` | 전체 동작 명세 및 스킬 사용 가이드 |
| `tools/` | CLIProxyAPI 등 유틸리티 바이너리 |

## Setup

`./scripts/setup.sh` 하나로 모든 환경이 셋업된다 (macOS, Linux, Windows 크로스 플랫폼 지원).

설치 항목 (7단계):
1. 시스템 의존성 — ffmpeg (오디오 변환), Node.js (QMD), curl
2. Python 3.12 + marker-pdf + markitdown — 3.10 미만이면 자동 설치
3. marker-pdf ML 모델 — surya OCR/layout/table 7종 (~2GB 사전 다운로드)
4. CLIProxyAPI — LLM 보정 프록시 + Codex OAuth 안내
5. QMD 검색 엔진 — GGUF 모델 3종 (embedding + reranking + generation) + collection 생성 + 인덱싱
6. 디렉토리 구조 — raw/, wiki/, output/ 하위 전체
7. 설정 파일 — Claude Code MCP, manifest, index

플래그: `--full`, `--skip-python`, `--skip-qmd`, `--skip-models`, `-h`

## Core Operations

11개 운영 스킬이 정의되어 있다.
- Claude Code: `.claude/commands/`에서 `/project:<스킬명>`으로 호출.
- Codex CLI: `.agents/skills/`에서 `$<스킬명>`으로 호출.

상세 명세는 [SCHEMA.md](SCHEMA.md) 참조.

### Tier 1 — 기본 루프
- **Catalog** (`/project:catalog`): raw 소스를 `raw/.manifest.md`에 등록, 비텍스트 파일 파싱.
- **Ingest** (`/project:ingest`): raw → wiki 승격. 소스 읽기 → 분석 → 문서 생성/갱신 → 색인 갱신.
- **Lint** (`/project:lint`): 위키 건강검진. 고아 페이지, 깨진 링크, frontmatter 누락, 모순, 구조 위반 탐지. 주 1회 권장.

### Tier 2 — 품질 유지
- **Supersede** (`/project:supersede`): 정보 대체 시 안전 갱신. `## Change log` 테이블에 이력 보존, 파급 효과 추적.
- **Score** (`/project:score`): 문서별 신뢰도 평가. frontmatter에 `confidence:` 확장 필드 추가.
- **Reindex** (`/project:reindex`): `wiki/index.md`와 주제별 맵 재구축.

### Tier 3 — 가치 창출
- **Query** (`/project:query`): 질문 → 답변 → 위키 강화 선순환. 단순 조회 시에는 wiki 수정 없이 답변만 제공.
- **Generate** (`/project:generate`): wiki → output 파생. 브리프, 온보딩, 리포트, 액션 아이템 도출.
- **Extract Actions** (`/project:extract-actions`): wiki에 흩어진 기존 마커(TODO, Open question, FIXME) 탐지·수집.

### Tier 4 — 스케일링
- **Audit** (`/project:audit`): 구조 + 커버리지 + 신뢰도 + 최신성 + 연결성 종합 감사. 월 1회 권장.
- **Trace Citation** (`/project:trace-citation`): 특정 사실의 근거를 raw 소스까지 역추적.

### Manifest 인제스트 상태
`raw/.manifest.md`에서 사용하는 상태값: `완료` | `미정` | `부분` | `보류`

## Frontmatter Schema

Every refined document requires this YAML frontmatter:

```yaml
---
title: Document title
owner: knowledge-system
status: draft | published | archived
updated: YYYY-MM-DD
tags: [tag1, tag2]
source: [raw/meetings/2026-04-06-topic.md]
confidence: high | medium | low | unverified  # optional, /project:score가 추가
---
```

`source` is critical — always link back to the raw material or meeting note that produced the document.
`confidence`는 `/project:score` 실행 시 자동 추가되는 선택적 필드이다.

## File Naming

- Date-prefixed for time-sensitive: `wiki/decisions/2026-04-06-decision-name.md`
- Kebab-case for topic-based: `wiki/systems/my-system.md`, `wiki/glossary/term-name.md`
- Raw docs mirror origin: `raw/meetings/2026-04-06-topic.md`
- Marker 파싱 결과: `raw/docs/filename.parsed.md` (원본 옆에 생성)

## Hard Rules (from AGENTS.md)

- **Don't write without evidence.** If unsure, use `TODO`, `Open question`, or `Assumption` markers.
- **Preserve raw originals.** Never destructively edit `raw/` content.
- **Always cite sources** in both frontmatter `source:` field and inline markdown links.
- **Separate concerns:** decisions go in `wiki/decisions/`, procedures in `wiki/playbooks/`, explanations in `wiki/systems|processes|projects/`. Never mix them in one document.
- **Update indexes** whenever creating or moving documents — check `wiki/index.md` and relevant topic maps.
- **Track contradictions** in `wiki/_meta/contradictions.md`.
- **Update manifest** when adding raw sources — `raw/.manifest.md`.

## Templates

Always start new documents from the matching template in `templates/`:
- `wiki-page.md` — wiki explanations
- `entity.md` — entity snapshots
- `glossary-term.md` — glossary entries
- `raw-note.md` — raw material
- `decision-adr.md` — ADRs
- `playbook.md` — operational procedures
- `index-map.md` — navigation maps

## Agent Workflow

에이전트가 작업할 때는 스킬을 사용한다.
- Claude Code: `.claude/commands/`의 `/project:<스킬명>`
- Codex CLI: `.agents/skills/`의 `$<스킬명>`

수동으로 raw → wiki 승격을 할 때의 절차:

1. `catalog <파일>` — raw 소스 등록 + 비텍스트 파싱.
2. `ingest <파일>` — wiki로 승격 (중복/모순 확인 → 문서 생성/갱신 → 색인 갱신 → 보고).
3. 정보 변경 시 `supersede <소스>` — 기존 문서 갱신 + Change log 기록 + 파급 효과 추적.

각 스킬의 상세 절차는 해당 스킬 파일과 [SCHEMA.md](SCHEMA.md)에 명세되어 있다.
재사용 에이전트 프롬프트는 `prompts/raw-to-wiki.md`와 `prompts/weekly-curation.md`에 있다.

## Commit Units

Keep commits atomic by type:
- raw ingest
- wiki promotion (ingest)
- decision extraction
- playbook update
- glossary cleanup
- index refresh
- output generation
- lint/meta update

## Search

QMD를 사용하여 위키를 검색할 수 있다. `./scripts/setup.sh`가 자동으로 collection을 생성하고 인덱싱한다.

### 검색 우선순위 (Hard Rule)

**위키 내용을 검색할 때는 반드시 QMD를 먼저 사용한다. Grep/Glob은 QMD로 충분하지 않을 때만 보조로 쓴다.**

| 상황 | 사용 도구 | 이유 |
|------|-----------|------|
| wiki/raw/output 내용 검색 (의미, 주제, 질문) | `mcp__qmd__query` | 시맨틱+키워드 하이브리드 검색, 랭킹 제공 |
| 특정 문서 전문 조회 | `mcp__qmd__get` / `mcp__qmd__multi_get` | 경로/docid로 빠른 조회 |
| 코드·설정·스크립트 파일 검색 (`.sh`, `.json`, `.yml` 등) | Grep / Glob | QMD 인덱싱 범위 밖 |
| 정확한 문자열·정규식 매칭이 필요할 때 | Grep | 패턴 매칭은 Grep이 정확 |
| 파일 존재 여부·경로 패턴 확인 | Glob | 파일시스템 탐색 |

### QMD 사용법
- **Claude Code 내부**: `mcp__qmd__query` 도구로 검색 (MCP 서버 `.claude/settings.json`에 설정됨).
- **터미널**: `qmd query "검색어" -c <collection-name>` (하이브리드 검색: BM25 + 벡터 + 리랭킹).
- wiki 변경 후 `qmd update && qmd embed`로 인덱스를 갱신한다.
