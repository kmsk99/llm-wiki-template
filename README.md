# LLM Wiki Template

Markdown 기반 지식 위키 템플릿입니다.
Karpathy LLM Wiki 패턴(raw → wiki → output)으로 운영합니다.

## 핵심 원칙
- **raw/** 에 원자료를 먼저 쌓는다 (불변).
- 검토 가능한 사실만 **wiki/** 로 승격한다 (Ingest).
- 축적된 지식에서 **output/** 을 파생한다 (Generate).
- 주기적으로 위키 건강도를 점검한다 (Lint).
- 사람은 읽고 승인하고, 에이전트는 정리·갱신·검색을 보조한다.

## 초기 셋업

```bash
# 1. 이 템플릿을 복사하여 새 프로젝트를 만든다
cp -r llm-wiki-template my-project-wiki
cd my-project-wiki
git init

# 2. 환경을 셋업한다
./scripts/setup.sh          # 기본 설치 (PDF 지원)
./scripts/setup.sh --full   # 전체 설치 (PDF + DOCX, XLSX, PPTX, 이미지, EPUB)
```

셋업 스크립트가 Python 3.10+, pip, marker-pdf 설치, 디렉토리 구조를 자동 확인·설치합니다.

### Marker (비텍스트 파일 파싱)
PDF, Excel, DOCX, PPTX 등 비텍스트 raw 파일을 Markdown으로 변환하는 데 사용합니다.
- 기본으로 CLIProxyAPI + LLM 보정을 사용합니다 (테이블/이미지 비전 기반 교정).
- LLM 없이 실행: `./scripts/parse-raw.sh --no-llm <파일>`
- CLIProxyAPI 셋업: `cd tools && ./cli-proxy-api -codex-login` → `./cli-proxy-api &`
- 파싱 스크립트: `scripts/parse-raw.sh`

## 시작 방법
1. Obsidian에서 이 폴더를 vault로 연다.
2. 회의/슬랙/전사/초안은 먼저 `raw/` 아래에 저장한다.
   - PDF, Excel 등 비텍스트 파일도 `raw/`에 저장한다.
3. Claude Code에서 스킬로 위키를 운영한다:
   - `/project:catalog` → raw 소스 등록 + 비텍스트 파싱
   - `/project:ingest` → wiki로 승격
   - `/project:query` → 위키에 질문
4. 수동으로 문서를 작성할 때는 `templates/`의 템플릿을 사용한다.
5. 상세 동작 명세는 [SCHEMA.md](SCHEMA.md) 참조.

## 폴더 구조
```text
.
├── raw/                    # Layer 1: 불변 원자료
│   ├── meetings/           #   회의록
│   ├── briefs/             #   초안, 검토 노트
│   ├── slack/              #   슬랙 발췌
│   ├── transcripts/        #   전사
│   ├── links/              #   링크 덤프
│   ├── files/              #   PDF, Excel 등 비텍스트 파일
│   ├── *.parsed.md         #   Marker로 파싱된 비텍스트 파일의 MD 변환본
│   └── .manifest.md        #   소스 목록 및 인제스트 상태
├── scripts/                # 유틸리티 스크립트
│   ├── setup.sh            #   초기 환경 셋업 (marker-pdf 설치 등)
│   └── parse-raw.sh        #   Marker 기반 비텍스트 → MD 파싱
├── wiki/                   # Layer 2: LLM이 유지보수하는 정제 문서
│   ├── index.md            #   마스터 네비게이션 맵
│   ├── index/              #   주제별 맵
│   ├── systems/            #   시스템 설명
│   ├── processes/          #   프로세스 설명
│   ├── projects/           #   프로젝트 설명
│   ├── decisions/          #   ADR/의사결정 기록
│   ├── playbooks/          #   운영 절차, 장애 대응
│   ├── entities/           #   브랜드, 고객, 파트너, 시스템
│   ├── glossary/           #   용어집
│   └── _meta/              #   모순 추적, 위키 건강도
├── output/                 # Layer 3: 위키 기반 파생물
│   ├── briefs/             #   의사결정 브리프
│   ├── onboarding/         #   온보딩 가이드
│   ├── action-items/       #   실행 항목
│   └── reports/            #   주간·월간 리포트
├── templates/              # 문서 템플릿
├── prompts/                # Codex/Claude Code용 재사용 프롬프트
├── tools/                  # CLIProxyAPI 등 유틸리티 바이너리
├── .claude/
│   ├── commands/           #   11개 위키 운영 스킬 (slash commands)
│   └── settings.json       #   MCP 서버 설정 (qmd)
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

## 스킬 사용법 (Claude Code)

이 레포의 `.claude/commands/`에 11개 위키 운영 스킬이 정의되어 있습니다.
Claude Code에서 `/project:` 접두어로 바로 호출할 수 있습니다.

### 전체 스킬 목록

| 스킬 | 용도 | 예시 |
|------|------|------|
| `/project:catalog` | raw 소스 등록 + 파싱 | `/project:catalog raw/files/report.pdf` |
| `/project:ingest` | raw → wiki 승격 | `/project:ingest raw/meetings/2026-04-09.md` |
| `/project:query` | 위키에 질문 | `/project:query 서비스 아키텍처는?` |
| `/project:lint` | 위키 건강검진 | `/project:lint --fix` |
| `/project:supersede` | 정보 대체 | `/project:supersede raw/meetings/2026-04-09.md` |
| `/project:score` | 신뢰도 평가 | `/project:score wiki/systems/` |
| `/project:generate` | output 문서 생성 | `/project:generate brief 서비스 현황` |
| `/project:extract-actions` | TODO/미해결 수집 | `/project:extract-actions` |
| `/project:audit` | 종합 감사 | `/project:audit --quick` |
| `/project:reindex` | 색인 재구축 | `/project:reindex` |
| `/project:trace-citation` | 출처 역추적 | `/project:trace-citation wiki/systems/my-system.md` |

### 자연어로도 작동합니다

slash command를 외울 필요 없이 자연어로 요청하면 Claude Code가 적절한 스킬을 선택합니다:

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
