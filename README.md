# LLM Wiki Template

Markdown 기반 지식 위키 템플릿입니다.
Karpathy LLM Wiki 패턴(raw → wiki → output)으로 운영합니다.

## 핵심 원칙
- **raw/** 에 원자료를 먼저 쌓는다 (불변).
- 검토 가능한 사실만 **wiki/** 로 승격한다 (Ingest).
- 축적된 지식에서 **output/** 을 파생한다 (Generate).
- 주기적으로 위키 건강도를 점검한다 (Lint).
- 사람은 읽고 승인하고, 에이전트는 정리·갱신·검색을 보조한다.

## 지원 환경

| 플랫폼 | 패키지 매니저 |
|--------|--------------|
| macOS | Homebrew |
| Linux (Ubuntu/Debian) | apt |
| Linux (Fedora/RHEL) | dnf / yum |
| Linux (Arch) | pacman |
| Windows (WSL / Git Bash / MSYS2) | winget / choco / scoop |

## 초기 셋업

```bash
# 1. 이 템플릿을 복사하여 새 프로젝트를 만든다
cp -r llm-wiki-template my-project-wiki
cd my-project-wiki
git init

# 2. 원스톱 환경 셋업
./scripts/setup.sh
```

### setup.sh가 설치하는 것들

| 단계 | 항목 | 설명 |
|------|------|------|
| 1/5 | 시스템 의존성 | poppler (pdftotext), ffmpeg (오디오 변환), Node.js (QMD), curl |
| 2/5 | Python + markitdown | Python 3.12 자동 설치, markitdown (DOCX, PPTX, XLSX 등 변환) |
| 3/5 | QMD 검색 엔진 | GGUF 모델 3종 + collection 생성 + 인덱싱 + 임베딩 |
| 4/5 | 디렉토리 구조 | raw/, wiki/, output/ |
| 5/5 | 설정 파일 | Claude Code MCP, manifest, index 확인 |

### 선택적 실행

```bash
./scripts/setup.sh --skip-python   # Python/markitdown 생략 (QMD만 셋업)
./scripts/setup.sh --skip-qmd      # QMD 생략
./scripts/setup.sh --skip-models   # 모델 다운로드 생략 (빠른 셋업)
./scripts/setup.sh -h              # 도움말
```

### 비텍스트 파일 파싱
PDF, Excel, DOCX, PPTX 등 비텍스트 raw 파일을 Markdown으로 변환합니다.
- PDF → pdftotext (poppler) — 빠르고 정확한 텍스트 추출
- 그 외 → MarkItDown — DOCX, PPTX, XLSX, 이미지, HTML, 오디오 등
- 파싱 스크립트: `scripts/parse-raw.sh`

## 시작 방법
1. Obsidian에서 이 폴더를 vault로 연다.
2. 회의/슬랙/전사/초안은 먼저 `raw/` 아래에 저장한다.
   - PDF, Excel 등 비텍스트 파일도 `raw/`에 저장한다.
3. Claude Code 또는 Codex CLI에서 스킬로 위키를 운영한다:
   - `/project:catalog` (Claude) / `$catalog` (Codex) → raw 소스 등록 + 비텍스트 파싱
   - `/project:ingest` (Claude) / `$ingest` (Codex) → wiki로 승격
   - `/project:query` (Claude) / `$query` (Codex) → 위키에 질문
4. 수동으로 문서를 작성할 때는 `templates/`의 템플릿을 사용한다.
5. 상세 동작 명세는 [SCHEMA.md](SCHEMA.md) 참조.

## 폴더 구조
```text
.
├── raw/                    # Layer 1: 불변 원자료 (하위 구조는 내용에 따라 생성)
│   ├── *.parsed.md         #   파싱된 비텍스트 파일의 MD 변환본
│   └── .manifest.md        #   소스 목록 및 인제스트 상태
├── scripts/                # 유틸리티 스크립트
│   ├── setup.sh            #   원스톱 환경 셋업 (크로스 플랫폼)
│   └── parse-raw.sh        #   비텍스트 → MD 파싱 (pdftotext + MarkItDown)
├── wiki/                   # Layer 2: LLM이 유지보수하는 정제 문서 (하위 구조는 내용에 따라 생성)
│   ├── index.md            #   마스터 네비게이션 맵
│   └── _meta/              #   모순 추적, 위키 건강도
├── output/                 # Layer 3: 위키 기반 파생물 (하위 구조는 내용에 따라 생성)
├── templates/              # 문서 템플릿
├── prompts/                # 재사용 에이전트 프롬프트
├── .claude/
│   ├── commands/           #   12개 위키 운영 스킬 (Claude Code)
│   └── settings.json       #   MCP 서버 설정 (qmd)
├── .agents/
│   └── skills/             #   12개 위키 운영 스킬 (Codex CLI)
├── CLAUDE.md               # LLM 운영 지침
├── SCHEMA.md               # 전체 동작 명세 및 스킬 사용 가이드
└── AGENTS.md               # 에이전트 작업 규칙
```

## 3레이어 워크플로우

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

### 핵심 동작
- **Catalog**: raw 소스를 manifest에 등록하고 비텍스트 파일을 파싱한다.
- **Ingest**: raw 소스를 읽고 wiki 문서를 생성·갱신한다 (핵심 파이프라인).
- **Query**: 질문에 답하면서 실질적 발견이 있을 때 wiki를 보충한다.
- **Lint**: 고아 페이지, 깨진 링크, 모순, 오래된 정보를 점검한다.
- **Supersede**: 기존 정보를 새 정보로 대체하고 Change log에 이력을 보존한다.
- **Score**: 문서별 신뢰도를 평가한다.
- **Generate**: wiki 지식을 기반으로 output 문서를 생성한다.
- **Extract Actions**: wiki에 흩어진 TODO, Open question 등을 수집한다.
- **Audit**: 구조, 커버리지, 신뢰도, 최신성, 연결성을 종합 점검한다.
- **Trace Citation**: 사실의 근거를 raw 소스까지 역추적한다.
- **Reindex**: wiki/index.md와 주제별 맵을 재구축한다.

## 스킬 사용법

12개 위키 운영 스킬이 두 에이전트 모두에서 사용 가능합니다.

| 스킬 | Claude Code | Codex CLI | 용도 |
|------|------------|-----------|------|
| catalog | `/project:catalog` | `$catalog` | raw 소스 등록 + 파싱 |
| ingest | `/project:ingest` | `$ingest` | raw → wiki 승격 |
| batch-ingest | `/project:batch-ingest` | `$batch-ingest` | 대량 파일 일괄 승격 |
| query | `/project:query` | `$query` | 위키에 질문 |
| lint | `/project:lint` | `$lint` | 위키 건강검진 |
| supersede | `/project:supersede` | `$supersede` | 정보 대체 |
| score | `/project:score` | `$score` | 신뢰도 평가 |
| generate | `/project:generate` | `$generate` | output 문서 생성 |
| extract-actions | `/project:extract-actions` | `$extract-actions` | TODO/미해결 수집 |
| audit | `/project:audit` | `$audit` | 종합 감사 |
| reindex | `/project:reindex` | `$reindex` | 색인 재구축 |
| trace-citation | `/project:trace-citation` | `$trace-citation` | 출처 역추적 |

### 자연어로도 작동합니다

slash command를 외울 필요 없이 자연어로 요청하면 에이전트가 적절한 스킬을 선택합니다:

- "새 회의록 올렸어, 위키에 반영해줘" → catalog + ingest
- "위키 상태 점검해줘" → lint
- "이 시스템이 뭐야?" → query
- "이 문서 근거가 맞아?" → trace-citation

### 권장 주기

| 주기 | 실행 스킬 |
|------|-----------|
| **일상** (새 소스 추가 시) | `catalog` → `ingest` |
| **주간** | `lint --fix` → `reindex` → `extract-actions` |
| **월간** | `audit` → `score` → `generate report weekly` |

### 대량 소스 처리 (Obsidian vault 등)

1000건 이상의 파일을 한번에 처리할 때는 batch-ingest → 정제 워크플로우를 사용합니다:

```
1. batch-ingest (대량 승격)
   └─ promote: 정제된 노트 → frontmatter만 추가하고 wiki/로 이동
   └─ merge:   같은 주제 노트들 → 하나의 wiki 문서로 통합
   └─ selective: 중요한 것만 선별 승격, 나머지 보류

2. lint --fix (구조 문제 자동 수정)

3. score (문서별 신뢰도 평가 → 낮은 품질 문서 식별)

4. ingest (score가 낮은 문서만 선별하여 재정제)

5. supersede (중복 문서 통합)

6. reindex (최종 색인 정비)
```

promote로 올린 문서는 `status: draft`로 들어가므로, score로 걸러서 필요한 것만 재정제하면 됩니다.

상세한 동작 명세는 [SCHEMA.md](SCHEMA.md)를 참조하세요.

## 커스터마이즈

이 템플릿을 프로젝트에 맞게 수정하세요:

1. **CLAUDE.md**: 프로젝트명, QMD collection 이름 등을 변경
2. **AGENTS.md**: 프로젝트 특화 규칙 추가
3. **wiki/entities/**: 하위 디렉토리를 프로젝트에 맞게 조정 (brands, customers 등)
4. **raw/.manifest.md**: 프로젝트 첫 소스를 등록
5. **.claude/settings.json**: QMD MCP 서버 경로를 환경에 맞게 수정

## 권장 파일명 규칙
- `raw/meetings/2026-04-06-topic.md`
- `wiki/decisions/2026-04-06-decision-name.md`
- `wiki/systems/kebab-case-name.md`
- `wiki/playbooks/kebab-case-playbook.md`
- `wiki/glossary/term-name.md`

## 기본 frontmatter
모든 정제 문서는 아래 필드를 기본으로 가집니다.

```yaml
---
title:
owner:
status: draft
updated: 2026-04-06
tags: []
source: []
---
```

## 운영 원칙
- 원본과 정제본을 분리한다.
- 사실 근거가 없는 내용은 쓰지 않는다.
- 추정이 필요한 내용은 `TODO`, `Assumption`, `Open question`으로 명시한다.
- 의사결정은 `wiki/decisions/`에 별도 문서로 남긴다.
- 실행 절차는 `wiki/playbooks/`로 분리한다.
- 문서 추가/변경 시 `wiki/index.md`와 관련 맵 문서를 함께 갱신한다.
- 모순 발견 시 `wiki/_meta/contradictions.md`에 기록한다.

## 검색

### Claude Code (권장)
- `/project:query <질문>` — 위키에 질문 (답변 + 위키 강화)
- QMD MCP 서버를 통한 자동 하이브리드 검색

### 터미널
```bash
qmd query "검색어" -c my-wiki   # 하이브리드 (BM25 + 벡터 + 리랭킹)
qmd search "키워드" -c my-wiki  # BM25 키워드 검색 (빠름)
qmd vsearch "의미 검색" -c my-wiki  # 벡터 시맨틱 검색
```

### Obsidian
- Obsidian 내장 검색 사용

### 인덱스 갱신
wiki 변경 후: `qmd update && qmd embed`
