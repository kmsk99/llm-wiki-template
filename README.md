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
| 1/5 | 시스템 의존성 | poppler (pdftotext), ffmpeg (오디오 변환), curl |
| 2/5 | Python + Docling | Python 3.12 자동 설치, Docling + 보조 파서 (HTML/HWP/HWPX/이미지/TXT/DOC) |
| 3/5 | Graphify 지식 그래프 | graphify CLI 설치 및 그래프 워크플로 준비 |
| 4/5 | 디렉토리 구조 | raw/, wiki/, output/ |
| 5/5 | 설정 파일 | Claude Code hooks, manifest, index 확인 |

### 선택적 실행

```bash
./scripts/setup.sh --skip-python   # 기존 Python/venv를 그대로 사용
./scripts/setup.sh -h              # 도움말
```

### 비텍스트 파일 파싱
PDF, Excel, DOCX, PPTX, HWP/HWPX, 이미지, HTML 등 비텍스트 raw 파일을 Markdown으로 변환합니다.
- PDF(텍스트 레이어) → pdftotext + LLM Markdown 정리
- PDF(스캔) → Docling OCR(OcrMac) + VLM
- HTML → `scripts/parse-html.py` 본문 추출
- HWP/HWPX → `scripts/parse-hwp.py`
- 이미지 → `scripts/parse-image.py` (GPT Vision 우선, 인증 실패 시 재로그인 안내)
- TXT/DOC → `scripts/parse-text.py`
- 그 외 (XLSX, DOCX, PPTX 등) → Docling 통합 변환
- 유지보수/복구 → `scripts/repair_parsed_artifacts.py` 로 zero/one-byte parsed, 중복 파일명, size suffix를 정리할 수 있습니다.
- 파싱 스크립트: `scripts/parse-raw.sh` → `scripts/parse_docling.py`

### 로컬 GPT/Vision 프록시 설정
`parse-raw.sh`, `parse-image.py`, `parse-hwp.py`, `parse_docling.py`는 repo 루트 `.env`에서 아래 값을 자동으로 읽습니다.

```bash
CLIPROXY_BASE_URL=http://127.0.0.1:8317/v1
CLIPROXY_API_KEY=<your-local-proxy-bearer>
DOCLING_OPENAI_MODEL=gpt-5.4-mini
```

직접 export하지 않아도 되며, GPT 인증이 만료되면 `parse-image.py`는 OCR fallback 대신 재로그인 안내를 출력합니다.
필요하면 `.env.example`을 `.env`로 복사해 시작하세요.

### CLIPROXY를 Docker로 실행하기
로컬에 CLIPROXY 서버를 띄워 `scripts/parse-raw.sh`, `parse-image.py`, `parse-hwp.py`, `parse_docling.py`가 같은 엔드포인트를 사용하도록 맞출 수 있습니다.

1. `.env.example`을 복사해 `.env`를 만들고 `CLIPROXY_API_KEY`를 원하는 bearer 값으로 수정합니다.

```bash
cp .env.example .env
$EDITOR .env
```

2. 로컬 전용 설정/인증/로그 디렉토리를 준비합니다. (`tools/` 아래는 기본적으로 gitignored)

```bash
mkdir -p tools/cliproxy/auth tools/cliproxy/logs

cat > tools/cliproxy/config.yaml <<'EOF'
port: 8317
auth-dir: "~/.cli-proxy-api"
request-retry: 3
quota-exceeded:
  switch-project: true
  switch-preview-model: true
api-keys:
  - "replace-with-your-local-proxy-bearer"
EOF
```

`api-keys` 값은 `.env`의 `CLIPROXY_API_KEY`와 동일하게 맞추는 것을 권장합니다.

3. Docker로 CLIPROXY 서버를 실행합니다.

```bash
docker run -d \
  --name cliproxy-api \
  --restart unless-stopped \
  -p 8317:8317 \
  -v "$(pwd)/tools/cliproxy/config.yaml:/CLIProxyAPI/config.yaml" \
  -v "$(pwd)/tools/cliproxy/auth:/root/.cli-proxy-api" \
  -v "$(pwd)/tools/cliproxy/logs:/CLIProxyAPI/logs" \
  eceasy/cli-proxy-api:latest
```

이미 같은 이름의 컨테이너가 있으면 먼저 정리한 뒤 다시 실행합니다.

```bash
docker rm -f cliproxy-api
```

4. Codex OAuth 로그인을 수행합니다.

```bash
docker exec -it cliproxy-api sh -lc '/CLIProxyAPI/CLIProxyAPI -codex-login -config /CLIProxyAPI/config.yaml'
```

브라우저 대신 디바이스 코드 플로우를 쓰려면 아래 명령을 사용합니다.

```bash
docker exec -it cliproxy-api sh -lc '/CLIProxyAPI/CLIProxyAPI -codex-device-login -config /CLIProxyAPI/config.yaml'
```

로그인 정보는 `tools/cliproxy/auth/`에 저장되므로 컨테이너를 재시작해도 유지됩니다.

5. 모델 목록과 실제 completion 호출로 동작을 확인합니다.

```bash
export CLIPROXY_API_KEY="$(awk -F= '/^CLIPROXY_API_KEY=/{print $2}' .env | tail -n1)"

curl -H "Authorization: Bearer ${CLIPROXY_API_KEY}" \
  http://127.0.0.1:8317/v1/models

curl -H "Authorization: Bearer ${CLIPROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8317/v1/chat/completions \
  --data '{
    "model": "gpt-5.4-mini",
    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    "max_tokens": 5
  }'
```

정상이라면 `/v1/models`는 사용 가능한 모델 목록을, `/v1/chat/completions`는 `ok` 응답을 반환합니다.

자주 쓰는 운영 명령:

```bash
docker logs -f cliproxy-api
docker restart cliproxy-api
docker stop cliproxy-api
```

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
│   ├── parse_docling.py    #   하이브리드 파싱 엔진 (PDF: pdftotext+LLM / 스캔: Docling OCR+VLM / 전용 파서 외 비PDF: Docling)
│   ├── parse-html.py       #   HTML 본문 중심 → MD 파싱
│   ├── parse-hwp.py        #   HWP/HWPX 전용 파서
│   ├── parse-image.py      #   GPT Vision 우선 이미지 파서
│   ├── parse-text.py       #   TXT/DOC 전용 파서
│   ├── repair_parsed_artifacts.py # parsed 복구 및 파일명 정리
│   └── parse-raw.sh        #   비텍스트 → MD 파싱 라우터
├── wiki/                   # Layer 2: LLM이 유지보수하는 정제 문서 (하위 구조는 내용에 따라 생성)
│   ├── index.md            #   마스터 네비게이션 맵
│   └── _meta/              #   모순 추적, 위키 건강도
├── output/                 # Layer 3: 위키 기반 파생물 (하위 구조는 내용에 따라 생성)
├── templates/              # 문서 템플릿
├── prompts/                # 재사용 에이전트 프롬프트
├── .claude/
│   ├── commands/           #   11개 위키 운영 스킬 (Claude Code)
│   └── settings.json       #   Claude Code hook 설정 (graphify 힌트)
├── .agents/
│   └── skills/             #   11개 위키 운영 스킬 (Codex CLI)
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

11개 위키 운영 스킬이 두 에이전트 모두에서 사용 가능합니다.

| 스킬 | Claude Code | Codex CLI | 용도 |
|------|------------|-----------|------|
| catalog | `/project:catalog` | `$catalog` | raw 소스 등록 + 파싱 |
| ingest | `/project:ingest` | `$ingest` | raw → wiki 승격 |
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

상세한 동작 명세는 [SCHEMA.md](SCHEMA.md)를 참조하세요.

## 커스터마이즈

이 템플릿을 프로젝트에 맞게 수정하세요:

1. **CLAUDE.md**: 프로젝트명과 운영 규칙을 변경
2. **AGENTS.md**: 프로젝트 특화 규칙 추가
3. **wiki/entities/**: 하위 디렉토리를 프로젝트에 맞게 조정 (brands, customers 등)
4. **raw/.manifest.md**: 프로젝트 첫 소스를 등록
5. **.claude/settings.json**: graphify hook 메시지를 프로젝트에 맞게 수정

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

## 지식 그래프 (Graphify)

[Graphify](https://github.com/safishamsi/graphify)는 raw/wiki/output 코퍼스를 관계 중심으로 탐색하기 위한 기본 지도입니다.
raw/wiki/output의 모든 마크다운과 코드 파일을 읽어 개념·파일 간 관계를 네트워크 그래프로 추출하고, Leiden 알고리즘으로 커뮤니티(주제 군집)를 자동 식별합니다. 출력 산출물:

| 파일 | 용도 |
|------|------|
| `graphify-out/GRAPH_REPORT.md` | god 노드, 커뮤니티 구조, 놀라운 연결, 추천 질문 |
| `graphify-out/graph.html` | 브라우저에서 열어보는 인터랙티브 그래프 |
| `graphify-out/graph.json` | 쿼리 가능한 구조화된 그래프 데이터 |
| `graphify-out/cache/` | SHA256 캐시 (변경된 파일만 재추출, gitignore됨) |

### 설치 (최초 1회)

```bash
# venv 활성화 후
pip install "graphifyy[mcp]"
graphify install           # 전역 Claude Code skill 등록 (~/.claude/skills/graphify/)
graphify claude install    # 프로젝트 CLAUDE.md + PreToolUse hook 등록
graphify hook install      # post-commit/post-checkout hook (코드 변경 시 AST 재빌드)
```

### 그래프 빌드

Claude Code 세션에서 자연스럽게 호출하세요. 대규모 코퍼스(>200 파일 또는 >2M 단어)면 skill이 서브폴더 선택을 먼저 요청합니다.

```
/graphify wiki
/graphify raw/회의
/graphify .
/graphify . --mode deep
/graphify . --update
```

### 그래프 질의

```bash
/graphify query "질문"
/graphify path "개념A" "개념B"
/graphify explain "개념"
```

## 검색

### Claude Code (권장)
- `/project:query <질문>` — 위키에 질문 (답변 + 위키 강화)
- `graphify-out/GRAPH_REPORT.md`와 `/graphify query|path|explain`를 우선 사용
- 정확한 문자열/경로 검색만 Grep/Glob으로 보완

### 터미널
```bash
graphify query "질문"
graphify path "개념A" "개념B"
graphify explain "개념"
rg "정확한 문구" wiki output raw
```

### Obsidian
- Obsidian 내장 검색 사용

### 그래프 갱신
wiki/raw/output 변경 후: `graphify . --update`

> `raw/`는 불변 원본이므로, raw 내부에 남아 있는 과거 검색 도구 언급은 역사적 기록으로 취급하고 현재 운영 규칙으로 사용하지 않습니다.
