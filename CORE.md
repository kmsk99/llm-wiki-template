# 기본 설치와 유지보수

Python 3.10 이상과 Git을 사용합니다. 기본 설치에는 모델 API나 Graphify가 필요하지 않습니다.

```sh
python3 scripts/setup_core.py
# 또는 ./scripts/setup.sh --core
```

Windows에서는 python3 대신 설치된 Python 명령을 사용하세요. 이후 명령의
`.venv/bin/python`은 Windows에서 `.venv/Scripts/python.exe`입니다.

## 검사

```sh
.venv/bin/python scripts/lint_wiki.py --check
.venv/bin/python scripts/lint_gate.py save /tmp/my-edit-before.json
# 문서 편집
.venv/bin/python scripts/lint_gate.py check /tmp/my-edit-before.json
.venv/bin/python scripts/sync_codex_skills.py --check
.venv/bin/python -m unittest discover -s tests
```

회귀 기준점 경로는 OS에 맞는 임시 디렉터리와 작업별 고유 이름을 사용합니다.
전체 lint의 기존 오류와 이번 편집에서 생긴 오류를 구분합니다. 외부 URL 응답,
실제 사람 승인, 사실의 진위까지 검사하는 것은 아닙니다.

## 커밋 훅

`python3 scripts/install_hooks.py`는 현재 Git hooks 경로에 관리용 wrapper를
설치합니다. 기존의 비관리 훅 또는 심링크가 있으면 실패하고 보존합니다.
기존 훅에서 `sh "$(git rev-parse --show-toplevel)/scripts/hooks/pre-commit"`을
호출하도록 연결한 뒤 나머지 검사를 실행하세요. 검사를 건너뛰고 설치가
완료됐다고 보고하지 않습니다.

raw 추가와 `.manifest.md` 내용 수정은 허용합니다. 기존 raw의 수정·삭제·이동·
유형 변경은 거부합니다. 예외가 꼭 필요하면 사유를 문서에 기록한 뒤 해당
커밋에서만 `ALLOW_RAW_MUTATION=1`을 사용합니다. 이 변수는 시크릿 검사를 우회하지 않습니다.

훅은 staged 텍스트의 알려진 패턴을 검사하며 일치한 값 자체를 출력하지 않습니다.
훅은 clone에 따라오지 않으므로 각 작업 사본에서 설치해야 합니다.
문서 lint·사본 drift는 별도 명령과 CI에서 검사하며 모든 커밋의 자동 게이트는 아닙니다.

## 공통 규칙과 프로젝트 설정

`SCHEMA.md`와 `.claude/commands`는 공통 정본입니다. `PROJECT.md`는 사용자
설정이며 업데이터에서 제외합니다. `AGENTS.md`·`CLAUDE.md`의 관리 블록 밖
내용, 사용자만의 스킬·템플릿은 보존합니다. 같은 이름의 관리 파일을 수정하면
업데이트 전에 충돌이 보고됩니다.

기존 SCHEMA.md에 사용자 규칙이 있다면 먼저 PROJECT.md로 분리하세요.
기존 진입 문서의 오래된 규칙과 새 공통 블록이 충돌하는지도 검토해야 합니다.
업데이터는 사용자 문장의 의미를 자동 판정하거나 삭제하지 않습니다.

```sh
python3 scripts/template_upgrade.py /path/to/my-wiki
python3 scripts/template_upgrade.py /path/to/my-wiki --apply
```

기본값은 dry-run입니다. 변경된 파일·충돌을 검토한 뒤 적용하고, 대상 저장소에서
기본 설치와 lint·스킬 동기화를 실행합니다. `--force`는 같은 이름의 관리 파일에
대한 수정을 덮어쓰므로 일반 업데이트에 사용하지 않습니다. v1의 디렉터리 단위
lock은 해당 디렉터리가 변경되지 않았을 때만 파일 단위 lock으로 이행합니다.
raw/wiki/output·PROJECT.md는 업데이트 대상이 아닙니다.

## Atlas에서 가져온 범위

원자료 보호와 스킬 동기화는 mason-atlas에서 검증한 방식을 일반화했습니다.
lint는 도메인·폴더명이 없는 기본 스키마용 검사기로 구성했고 회귀 기준점은
실행 가능한 pickle 대신 JSON으로 저장합니다. 사람 확인은 verify 지침과
메타데이터 검사를 제공하며 사용자의 실제 확인을 대신하지 않습니다.

프로젝트 lifecycle, 벡터 검색, 무인 주간 점검과 특정 모델·프록시 설정은 이번
기본 구성에 포함하지 않습니다. 사용자별 데이터나 평가 질문도 배포하지 않습니다.
