# Reindex: 색인 재구축

`wiki/index.md`와 `wiki/index/` 하위 맵 문서를 현재 wiki 상태에 맞게 재구축한다.
Ingest 후 자동으로 색인이 갱신되지만, 수동 문서 이동이나 대량 변경 후에는 이 스킬로 전체 색인을 재구축한다.

## 입력

$ARGUMENTS

- 인자가 없으면: 전체 색인을 재구축한다.
- 주제가 주어지면: 해당 주제의 index 맵만 갱신한다.

## 실행 절차

### 1. 전체 문서 스캔
1. wiki/ 하위의 모든 .md 파일을 수집한다.
2. 각 문서의 frontmatter에서 title, tags, status, updated를 읽는다.
3. status가 `archived`인 문서는 별도 섹션으로 분리한다.

### 2. 마스터 인덱스 갱신 (wiki/index.md)
4. 다음 구조로 wiki/index.md를 갱신한다:
   - 디렉토리별 문서 목록 (systems, processes, projects, decisions, playbooks, entities, glossary)
   - 각 항목: `- [title](경로) — 한줄 설명`
   - 최근 갱신 문서 Top 10

### 3. 주제별 맵 갱신 (wiki/index/)
5. 태그 기반으로 주제별 맵을 갱신하거나 생성한다.
6. 기존 맵의 수동 편집 내용(설명, 그룹핑)은 보존한다.

### 4. Cross-link 정비
7. 문서 본문의 링크 중 경로가 변경된 것을 탐지한다.
8. 수정 가능한 링크를 갱신한다.

## 출력

```
## Reindex Report

### 갱신된 색인
- wiki/index.md: N개 항목 갱신
- wiki/index/topic-map.md: ...

### 문서 통계
| 디렉토리 | 문서 수 |
|----------|---------|

### 수정된 링크
| 문서 | 이전 링크 | 새 링크 |
|------|-----------|---------|
```

## 규칙
- 색인 갱신만 한다. 문서 내용은 변경하지 않는다 (깨진 링크 수정 제외).
- 기존 index 문서의 수동 편집 내용을 최대한 보존한다.
- archived 문서는 별도 섹션에 표시하되 삭제하지 않는다.
