# LLM Wiki Template

회의록·문서·참고자료를 출처가 연결된 Markdown 위키로 정리하는 템플릿입니다. Claude Code와 Codex CLI에서 원자료 등록, 위키 갱신, 검색, 근거 확인을 같은 규칙으로 수행합니다.

[시작하기](#시작하기) · [운영 가이드](GUIDE.md) · [문서 규칙](SCHEMA.md) · [기여](CONTRIBUTING.md)

## 어떻게 쓰나요?

```text
raw/                  wiki/                   output/
회의록·PDF·원자료  →   출처를 남긴 지식 문서  →  브리프·리포트·실행 항목
        catalog → ingest               generate
```

원자료는 보존하고, 위키에는 확인 가능한 근거를 남깁니다. 에이전트가 정리·갱신·검색을 돕고 사람이 결과를 검토합니다.

- **수집과 정리:** PDF·오피스 문서·이미지 등의 파싱과 원자료 등록
- **검색과 근거 확인:** Graphify 관계 탐색과 원문까지의 출처 추적
- **유지보수:** 링크·구조 점검, 모순 기록, 변경된 정보의 대체

## 시작하기

이 저장소를 복사하거나 GitHub에서 새 저장소로 가져온 뒤 실행하세요.

```sh
git clone https://github.com/kmsk99/llm-wiki-template.git my-project-wiki
cd my-project-wiki
python3 scripts/setup_core.py
```

기본 설치는 Python 3.10 이상과 Git이 필요합니다. `.venv`에 PyYAML을 설치하고,
스킬 사본과 원자료 보호·시크릿 검사 훅을 준비합니다. Graphify나 LLM 인증은 필요하지 않습니다.
기존 커밋 훅이 있으면 보존하고 수동 연결 방법을 안내합니다.

`PROJECT.example.md`를 `PROJECT.md`로 복사해 프로젝트 설정을 적고, `raw/`에 첫 자료를 넣으세요. 에이전트에 다음처럼 요청할 수 있습니다.

> 새 회의록을 등록하고 위키에 반영해줘.
>
> 이 결정의 근거를 원문까지 찾아줘.

## 기본 보호 장치

- 원자료의 수정·삭제를 커밋 단계에서 차단하고 알려진 시크릿 패턴을 검사합니다.
- 문서의 메타데이터·출처·링크를 검사하고, 편집 전후 새 오류를 비교합니다.
- Claude Code·Codex·OMP가 동일한 스킬 정본을 사용하도록 동기화합니다.
- AI의 근거 강도(`confidence`)와 사람의 확인(`verified`)을 구분합니다.

[검사·업데이트 방법](CORE.md) · [선택 파서·Graphify 설치](GUIDE.md)

## 에이전트별 사용

| 환경 | 스킬 위치 | 호출 예시 |
| --- | --- | --- |
| Claude Code | `.claude/commands/` | `/project:catalog`, `/project:ingest` |
| Codex CLI · OMP | `.agents/skills/` | `$catalog`, `$ingest` |

12개 운영 스킬의 상세 설명, 파싱 설정, 템플릿 업그레이드, Graphify 사용법은 [운영 가이드](GUIDE.md)에 있습니다.

## 폴더 안내

| 경로 | 내용 |
| --- | --- |
| `raw/` | 원자료와 등록 매니페스트 |
| `wiki/` | 지식 문서, 결정, 절차, 색인 |
| `output/` | 위키에서 파생한 결과물 |
| `templates/`, `prompts/` | 문서 틀과 작업 지침 |
| `scripts/` | 환경 설치, 파싱, 점검, 업그레이드 |

Markdown 파일을 직접 읽거나 Obsidian 볼트로 열 수 있습니다.
