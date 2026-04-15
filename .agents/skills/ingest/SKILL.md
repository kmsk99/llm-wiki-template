---
name: ingest
description: "Raw 소스를 읽고 wiki 문서를 생성/갱신하는 핵심 파이프라인. raw → wiki 승격 시 사용."
---

# Ingest: Raw → Wiki 승격

새 raw 소스를 읽고 wiki/ 문서를 생성하거나 갱신하는 핵심 파이프라인.

## 입력

$ARGUMENTS

- 인자가 없으면: `raw/.manifest.md`에서 인제스트 상태가 `미정`인 소스를 모두 찾아 처리한다.
- 파일 경로가 주어지면: 해당 raw 소스만 처리한다.
- `--dry-run`이 붙으면: 실제 파일 변경 없이 계획만 출력한다.

## 실행 절차

### Phase 1: 소스 읽기
1. 대상 raw 소스를 식별한다.
   - 인자가 없으면 `raw/.manifest.md`에서 인제스트 상태가 `미정` 또는 `부분`인 소스를 수집한다.
2. `raw/.manifest.md`에 등록되지 않은 소스이면 먼저 `/project:catalog`을 안내한다.
3. **비텍스트 파일(PDF, XLSX, DOCX, PPTX, 이미지 등)이면**:
   - `scripts/parse-raw.sh <파일>`로 파싱하여 `.parsed.md`를 생성한다 (PDF는 텍스트 레이어 감지 시 pdftotext+LLM, HTML/HWP/HWPX/이미지/TXT/DOC는 전용 파서, 그 외는 Docling).
4. 파싱된 `.parsed.md` 또는 원본 텍스트를 읽는다.

### Phase 2: 분석
5. 핵심 사실, 결정사항, 반복 절차, 용어 후보, 엔티티를 추출한다.
6. 기존 wiki/ 문서와 **중복/모순**을 확인한다.
   - 중복이면 기존 문서를 갱신한다.
   - 모순이면 `wiki/_meta/contradictions.md`에 기록한다.
7. 새 문서를 만들지, 기존 문서를 갱신할지 결정한다.

### Phase 3: 문서 생성/갱신
8. `templates/` 디렉토리의 적절한 템플릿을 사용하여 문서를 작성한다.
   - 시스템 → `wiki/systems/` (wiki-page.md)
   - 프로세스 → `wiki/processes/` (wiki-page.md)
   - 프로젝트 → `wiki/projects/` (wiki-page.md)
   - 의사결정 → `wiki/decisions/` (decision-adr.md)
   - 운영절차 → `wiki/playbooks/` (playbook.md)
   - 엔티티 → `wiki/entities/` (entity.md)
   - 용어 → `wiki/glossary/` (glossary-term.md)
9. frontmatter를 완전히 채운다:
   - `source:` — 원본 raw 파일 경로 (`.parsed.md` 아님)
   - `updated:` — 오늘 날짜
   - `status: draft`
   - `tags:` — 관련 태그
10. 본문에서 관련 wiki 페이지를 상대경로 링크로 연결한다 (Cross-link).

### Phase 4: 색인 갱신
11. `wiki/index.md` 마스터 맵을 갱신한다.
12. 관련 `wiki/index/` 주제별 맵을 갱신한다.
13. `raw/.manifest.md`에서 해당 소스의 인제스트 상태를 갱신한다:
    - 모든 핵심 사실이 반영되었으면 → `완료`
    - 일부만 반영되었으면 → `부분` (비고에 사유 기록)

### Phase 5: 보고
14. 최종 보고를 출력한다:
    - 📄 변경/생성된 파일 목록
    - 📎 반영한 source
    - 🔗 새로 생성된 cross-link
    - ⚠️ 발견된 모순 (contradictions.md에 기록됨)
    - ❓ Open question / TODO

## 절대 규칙
- 근거 없는 내용을 쓰지 않는다. 불확실하면 `TODO` 또는 `Open question`으로 남긴다.
- raw/ 원본은 절대 수정하지 않는다.
- 하나의 문서에 정책, 절차, 의사결정을 섞지 않는다.
- 한 번의 ingest에서 여러 wiki 페이지를 생성/갱신할 수 있다.
