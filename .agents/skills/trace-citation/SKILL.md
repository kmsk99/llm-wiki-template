---
name: trace-citation
description: "특정 사실의 근거를 raw 소스까지 역추적한다."
---

# Trace Citation: 출처 추적

특정 사실이나 문서의 근거를 raw 소스까지 역추적한다.

## 입력

$ARGUMENTS

형식: `<wiki 문서 경로 또는 사실/키워드>`

예시:
- `wiki/systems/sajang-link.md` → 이 문서의 모든 사실을 소스까지 추적
- `월 구독료 29000원` → 이 사실의 근거를 찾음
- `wiki/decisions/2026-04-06-pricing.md#결정사항` → 특정 섹션의 근거 추적

## 실행 절차

### 문서 단위 추적
1. 대상 wiki 문서를 읽는다.
2. frontmatter `source:` 필드의 raw 파일이 실제 존재하는지 확인한다.
3. 해당 raw 소스를 읽고, wiki 문서의 핵심 사실이 실제로 raw에 있는지 대조한다.
4. 각 사실에 대해 추적 결과를 표시한다:
   - ✅ **Traced**: raw 소스에서 직접 확인됨
   - 🟡 **Inferred**: raw에 암시되어 있으나 명시적이지 않음
   - ❌ **Untraced**: raw 소스에서 근거를 찾을 수 없음
   - 🔄 **Multi-source**: 여러 raw 소스에서 확인됨

### 사실 단위 추적
1. 키워드로 wiki 문서를 검색한다.
2. 해당 사실이 포함된 문서를 찾는다.
3. 문서의 source 필드를 따라 raw까지 추적한다.
4. raw에서 해당 사실의 원문을 찾아 인용한다.

## 출력

```
## Citation Trace Report

### 대상: {문서/사실}

### 추적 결과
| 사실 | 상태 | Raw 소스 | 원문 위치 |
|------|------|----------|-----------|

### 요약
- ✅ Traced: N개
- 🟡 Inferred: N개
- ❌ Untraced: N개
- 🔄 Multi-source: N개

### 신뢰도 평가
전체 추적률: {비율}% — {평가}
```

## 규칙
- 추적은 읽기 전용이다. 문서를 수정하지 않는다.
- Untraced 사실이 발견되면 후속 조치를 안내한다:
  - 신뢰도 재평가가 필요하면 → `/project:score <문서>`
  - 출처를 찾아 보강해야 하면 → 해당 raw 소스를 `/project:ingest`
  - 근거 없는 사실이면 → `/project:lint`로 지식 공백 기록
- raw 소스의 원문을 인용할 때는 핵심 부분만 발췌한다.
