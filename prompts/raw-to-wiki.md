---
title: Raw to Wiki Prompt
owner: knowledge-system
status: draft
updated: 2026-04-06
tags: [prompts, workflow]
source: []
---

# Raw to Wiki Prompt

다음 규칙으로 이 repo를 정리해줘.

1. 반드시 `AGENTS.md`를 먼저 읽고 따른다.
2. 내가 지정한 `raw/` 문서를 읽는다.
   - **비텍스트 파일(PDF, XLSX, DOCX, PPTX 등)이면** 먼저 `scripts/parse-raw.sh <파일>`로 Marker 파싱하여 `.parsed.md`를 생성한 뒤, 그 파일을 읽는다.
3. 핵심 사실, 결정사항, 반복 절차, 용어 후보를 추출한다.
4. 기존 `wiki/`, `decisions/`, `playbooks/`, `entities/`, `glossary/`와 중복 여부를 확인한다.
5. 필요한 경우에만 새 문서를 만들고, 아니면 기존 문서를 갱신한다.
6. 모든 정제 문서에는 frontmatter와 `source`를 채운다 (원본 파일 경로 사용, `.parsed.md` 아님).
7. 새 문서나 큰 변경이 생기면 관련 `index/` 문서도 갱신한다.
8. 근거가 없는 내용은 쓰지 말고 `Open question`으로 남긴다.

최종 출력 형식:
- 변경 파일
- 반영한 source
- 추출된 decision / playbook / glossary 후보
- 아직 확인이 필요한 항목
