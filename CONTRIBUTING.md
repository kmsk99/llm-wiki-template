# Contributing

이 저장소는 Karpathy LLM Wiki 패턴(raw → wiki → output)으로 운영합니다.

## 문서 수명주기
1. **수집**: 아직 정리되지 않은 정보는 먼저 `raw/`에 넣고 `raw/.manifest.md`를 갱신합니다.
   - PDF, Excel, DOCX, PPTX 등 비텍스트 파일도 `raw/`에 저장합니다.
2. **파싱**: 비텍스트 파일은 `scripts/parse-raw.sh`로 Marker 파싱하여 `.parsed.md`를 생성합니다.
3. **승격(Ingest)**: 검토 가능한 사실만 `wiki/` 하위 디렉토리로 옮깁니다.
3. **연결**: 관련 문서 링크와 `wiki/index.md`를 갱신합니다.
4. **검토**: source 누락, 중복, 충돌 여부를 확인합니다.
5. **파생(Generate)**: 축적된 wiki 지식에서 `output/`을 생성합니다.

## 문서 작성 체크리스트
- [ ] 적절한 템플릿에서 시작했는가?
- [ ] frontmatter를 채웠는가?
- [ ] `updated` 날짜를 갱신했는가?
- [ ] `source`를 남겼는가? (원본 파일 경로 사용, `.parsed.md` 아님)
- [ ] 결정은 `wiki/decisions/`, 절차는 `wiki/playbooks/`로 분리했는가?
- [ ] `wiki/index.md` 및 관련 맵 문서를 갱신했는가?
- [ ] `raw/.manifest.md`를 갱신했는가? (raw 추가 시)

## 권장 커밋 단위
- raw ingest
- wiki promotion
- decision extraction
- playbook update
- glossary cleanup
- index refresh

## 검토 기준
- 사실과 해석이 구분되어 있는가?
- 같은 내용이 여러 곳에 충돌되게 적혀 있지 않은가?
- 출처 없이 확정적으로 쓴 문장이 없는가?
