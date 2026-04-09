# AGENTS.md

이 레포는 암묵지를 Markdown으로 저장·정제하는 knowledge repo다.
Karpathy LLM Wiki 패턴(raw → wiki → output)으로 운영한다.
에이전트는 아래 규칙을 반드시 따른다.

## 목적
- `raw/`에 쌓인 원자료를 `wiki/` 체계로 승격한다 (Catalog → Ingest).
- `wiki/`에 축적된 지식을 `output/`으로 파생한다 (Generate).
- 사람이 검토할 수 있도록 변경 근거를 남긴다.
- 문서 간 링크와 색인을 유지한다 (Cross-link, Reindex).
- 주기적으로 위키 건강도를 점검한다 (Lint, Score, Audit).
- 정보 변경 시 안전하게 대체하고 이력을 보존한다 (Supersede).

## 스킬

11개 운영 스킬이 두 에이전트 시스템에서 사용 가능하다.

| 에이전트 | 스킬 위치 | 호출 방식 |
|----------|-----------|-----------|
| Claude Code | `.claude/commands/*.md` | `/project:<스킬명>` |
| Codex CLI | `.agents/skills/<스킬명>/SKILL.md` | `$<스킬명>` 또는 자동 매칭 |

두 시스템의 스킬 내용은 동일하다. 상세 명세는 [SCHEMA.md](SCHEMA.md) 참조.

## 절대 규칙
1. **모르면 쓰지 말 것.** 근거가 불충분하면 `TODO` 또는 `Open question`으로 남긴다.
2. **원본(raw)은 보존할 것.** 의미를 바꾸는 편집, 삭제, 재해석은 금지한다.
3. **정제 문서는 출처를 남길 것.** `source:` frontmatter와 본문 링크를 채운다.
4. **의사결정은 분리할 것.** 결정사항을 일반 위키 문서에만 묻어두지 말고 `wiki/decisions/`에도 기록한다.
5. **절차는 분리할 것.** 반복 가능한 운영 방법은 `wiki/playbooks/`로 승격한다.
6. **색인을 갱신할 것.** 의미 있는 문서를 추가하면 `wiki/index.md`와 관련 맵 문서를 업데이트한다.
7. **manifest를 갱신할 것.** raw 소스 추가 시 `raw/.manifest.md`를 업데이트한다.
8. **모순을 추적할 것.** 문서 간 충돌 발견 시 `wiki/_meta/contradictions.md`에 기록한다.

## 문서 작성 규칙
- 정제 문서에는 frontmatter를 반드시 포함한다.
- `updated:` 값은 실제 수정일로 갱신한다.
- 파일명은 소문자 kebab-case 또는 날짜 접두 규칙을 사용한다.
- 링크는 가능한 한 표준 Markdown 상대경로 링크를 사용한다.
- 문서 첫 부분에 한 줄 요약 또는 목적을 넣는다.

## 폴더별 역할

### raw/ — 불변 원본
원자료 저장소. 회의록, 슬랙 발췌, 전사, 초안, 링크 덤프, PDF/Excel/PPTX 등 바이너리 파일 포함.
- `.manifest.md`로 전체 소스와 인제스트 상태를 추적한다.
  - 인제스트 상태: `완료` | `미정` | `부분` | `보류` (이 4가지만 사용).
- 비텍스트 파일은 Marker(`marker-pdf`) 또는 MarkItDown으로 파싱하여 `.parsed.md`를 생성한 후 인제스트한다.
  - PDF → Marker (CLIProxyAPI + LLM 보정)
  - 그 외 (XLSX, DOCX, PPTX, 이미지, HTML, 오디오 등) → MarkItDown
- `.parsed.md`는 파생물이므로 원본과 동일하게 수정·삭제 금지 대상은 아니지만, 재파싱으로 재생성할 수 있다.

### wiki/ — 정제 문서 전체
| 하위 디렉토리 | 역할 |
|---------------|------|
| `systems/` | 시스템 설명 |
| `processes/` | 프로세스 설명 |
| `projects/` | 프로젝트 설명 |
| `decisions/` | ADR 형식의 의사결정 기록 |
| `playbooks/` | 운영 절차, 대응 runbook, 온보딩 절차 |
| `entities/` | 고객, 브랜드, 파트너, 시스템, 데이터소스 등 핵심 객체 |
| `glossary/` | 용어 정의와 동의어 |
| `index.md` | 마스터 네비게이션 맵 |
| `index/` | 주제별 맵 |
| `_meta/` | 모순 추적, 위키 건강도 |

### output/ — 파생물
위키 지식 기반의 행동 지향 문서. briefs, onboarding, action-items, reports.

## 환경 셋업

`./scripts/setup.sh` 하나로 모든 의존성이 설치된다 (macOS, Linux, Windows 지원).

설치 항목:
1. 시스템 의존성 (ffmpeg, Node.js, curl)
2. Python 3.12 + marker-pdf + markitdown (자동 설치)
3. marker-pdf ML 모델 (surya OCR/layout/table 7종)
4. CLIProxyAPI (LLM 보정 프록시)
5. QMD 검색 엔진 (GGUF 모델 3종 + collection + 인덱싱)
6. 디렉토리 구조
7. 설정 파일 (Claude Code MCP, manifest, index)

## 권장 작업 흐름

각 작업은 스킬로 실행한다.

### Catalog + Ingest (raw → wiki)
1. `catalog <파일>` — raw 소스를 manifest에 등록, 비텍스트 파일 파싱.
2. `ingest <파일>` — wiki로 승격:
   - 기존 `wiki/` 문서와 중복/모순 확인.
   - 새 문서 생성 또는 기존 문서 갱신 (템플릿 사용).
   - frontmatter `source:`에 원본 파일 경로 기록 (`.parsed.md` 아님).
   - `wiki/index.md`와 관련 링크 갱신.
   - `raw/.manifest.md` 인제스트 상태를 `완료` 또는 `부분`으로 갱신.

### Supersede (정보 변경)
- `supersede <소스> [wiki 문서]` — 변경된 부분만 갱신, `## Change log` 테이블에 이력 보존, 파급 효과 추적.

### Generate (wiki → output)
- `generate <유형> [주제]` — wiki 지식 기반 output 생성.
- frontmatter `source:`에 기반 wiki 페이지를 명시한다.

### Lint / Score / Audit
- `lint [--fix]` — 구조적 건강도 점검 (주 1회).
- `score [문서]` — 신뢰도 평가, frontmatter에 `confidence:` 추가.
- `audit` — 종합 감사 (월 1회).

## 금지 사항
- 출처 없는 정책/수치/역할 정의를 사실처럼 쓰지 말 것
- `raw/` 내용을 정제 문서로 옮기며 맥락을 임의로 덧붙이지 말 것
- 하나의 문서에 정책, 절차, 의사결정을 전부 섞지 말 것
- `output/`에서 wiki에 없는 새로운 사실을 만들지 말 것
- 정보 대체 시 근거(새 소스) 없이 추측으로 대체하지 말 것
- manifest 인제스트 상태에 `완료`/`미정`/`부분`/`보류` 외의 값을 사용하지 말 것
