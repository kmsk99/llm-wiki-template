---
name: lint
description: "Wiki 구조적 건강도를 점검한다. 고아 페이지, 깨진 링크, frontmatter 누락, 모순, 구조 위반 탐지. 주 1회 권장."
---

# Lint: 위키 건강검진

wiki/ 전체의 구조적 건강도를 점검하고 문제를 보고한다.
주 1회 정기 실행을 권장한다 (SCHEMA.md 참조). 더 포괄적인 점검은 `/project:audit`를 사용한다.

## 입력

$ARGUMENTS

- 인자가 없으면: wiki/ 전체를 점검한다.
- 디렉토리가 주어지면: 해당 하위만 점검한다 (예: `wiki/systems/`).
- `--fix`가 붙으면: 자동 수정 가능한 항목을 직접 고친다.

## 점검 항목

### 1. 고아 페이지 (Orphan Pages)
- `wiki/index.md`나 다른 문서에서 링크되지 않는 페이지를 찾는다.
- **Graphify 교차 확인:** `graphify-out/GRAPH_REPORT.md`와 `graph.json`에서 엣지 수가 0이거나 1인 노드를 함께 나열한다. 파일 링크가 있어도 그래프에서 고립된 노드는 **의미적 고아**로 분류한다.
- 심각도: ⚠️ Warning

### 2. 깨진 링크 (Broken Links)
- 본문의 Markdown 링크 중 실제 파일이 존재하지 않는 것을 찾는다.
- 심각도: 🔴 Error

### 3. Frontmatter 불완전
- 필수 필드 누락 확인: `title`, `owner`, `status`, `updated`, `tags`, `source`
- `source:`가 비어있거나 존재하지 않는 raw 파일을 가리키는지 확인
- `updated:` 날짜가 30일 이상 오래된 문서 표시
- 심각도: 🔴 Error (누락) / ⚠️ Warning (오래됨)

### 4. 문서 간 모순
- 동일 주제를 다루는 문서들에서 상충되는 정보를 탐지한다.
- 발견 시 `wiki/_meta/contradictions.md`에 기록한다.
- 심각도: 🔴 Error

### 5. 구조 위반
- 의사결정이 `wiki/decisions/` 외부에 있는지
- 운영절차가 `wiki/playbooks/` 외부에 있는지
- 엔티티가 `wiki/entities/` 외부에 있는지
- 용어 정의가 `wiki/glossary/` 외부에 있는지
- 하나의 문서에 정책/절차/결정이 혼재되어 있는지
- 심각도: ⚠️ Warning

### 6. 색인 정합성
- `wiki/index.md`에 모든 주요 문서가 포함되어 있는지
- `wiki/index/` 주제별 맵이 최신인지
- 심각도: ⚠️ Warning

### 7. Manifest 정합성
- `raw/.manifest.md`에 등록되지 않은 raw 파일이 있는지
- manifest에서 `미정`인데 이미 wiki 문서가 있는 소스
- 심각도: ⚠️ Warning

### 8. 지식 공백 (Knowledge Gaps)
- 문서에 `TODO`, `Open question`, `TBD`, `Assumption` 마커가 있는 항목을 수집한다.
- 심각도: ℹ️ Info

## 출력 형식

```
## Wiki Lint Report — {날짜}

### Summary
- 🔴 Errors: N
- ⚠️ Warnings: N
- ℹ️ Info: N
- 📄 검사한 문서: N

### Errors
| 파일 | 항목 | 설명 |
|------|------|------|
| ... | ... | ... |

### Warnings
| 파일 | 항목 | 설명 |
|------|------|------|
| ... | ... | ... |

### Knowledge Gaps
| 파일 | 마커 | 내용 |
|------|------|------|
| ... | ... | ... |

### Recommendations
- ...
```

## --fix 모드에서 자동 수정하는 항목
- frontmatter `updated:` 갱신
- `wiki/index.md`에 누락된 문서 추가
- `raw/.manifest.md`에 누락된 파일 등록 (상태: `미정`)
- `raw/.manifest.md`에서 이미 wiki 문서가 있는 `미정` 항목을 `완료`로 갱신
- 깨진 링크 중 파일명 변경으로 추적 가능한 것 수정

## 자동 수정하지 않는 항목 (사람 확인 필요)
- 문서 간 모순 해소
- 구조 위반 수정 (문서 이동/분리)
- 고아 페이지 삭제 여부
