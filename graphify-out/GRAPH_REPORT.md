# Graph Report - /Users/mason/project/personal/llm-wiki-template  (2026-04-18)

## Corpus Check
- 9 files · ~13,329 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 110 nodes · 203 edges · 8 communities detected
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `collapse_blank_lines()` - 10 edges
2. `repair_filename()` - 9 edges
3. `build_markdown()` - 9 edges
4. `parse_file()` - 7 edges
5. `main()` - 6 edges
6. `main()` - 6 edges
7. `extract_hwpx_text()` - 6 edges
8. `build_markdown()` - 6 edges
9. `build_markdown()` - 6 edges
10. `best_node_from_html()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `env_or_dotenv()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/parse_docling.py → /Users/mason/project/personal/llm-wiki-template/scripts/env_defaults.py
- `main()` --calls--> `parse_args()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/parse_docling.py → /Users/mason/project/personal/llm-wiki-template/scripts/parse-pdf.py
- `env_or_dotenv()` --calls--> `extract_hwpx_preview_image_text()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/env_defaults.py → /Users/mason/project/personal/llm-wiki-template/scripts/parse-hwp.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.27
Nodes (18): build_markdown(), collapse_blank_lines(), extract_html_text(), extract_hwp_preview_text(), extract_hwp_text(), extract_hwp_text_hwp5txt(), extract_hwp_text_libhwp(), extract_hwpx_preview_image_text() (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.24
Nodes (15): canonical_duplicate(), cleaned_filename_hint(), display_path(), iter_raw_files(), looks_mojibake(), main(), needs_parse_refresh(), parse_args() (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.19
Nodes (15): build_data_url(), caption_image(), extract_message_text(), _find_hybrid_bin(), hybrid_server(), main(), mime_type_for(), parse_args() (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.2
Nodes (15): _build_ocr_options(), create_converter(), dedup_merged_cells(), _dedup_table_row(), _llm_format_markdown(), main(), parse_file(), _pdf_has_text_layer() (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.29
Nodes (12): build_data_url(), build_markdown(), call_gpt_vision(), extract_message_text(), get_tesseract_lang(), is_auth_error(), load_image_metadata(), main() (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.44
Nodes (10): best_node(), best_node_from_html(), candidate_score(), clean_node(), fallback_markdown(), iter_candidate_soups(), main(), meta_content() (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.25
Nodes (4): env_or_dotenv(), read_dotenv_value(), EnvDefaultsTests, HwpParserTests

### Community 7 - "Community 7"
Cohesion: 0.39
Nodes (5): build_markdown(), main(), read_doc_file(), read_text_file(), ImageParserTests

## Knowledge Gaps
- **9 isolated node(s):** `pdftotext로 PDF 텍스트 레이어 추출. 텍스트가 있으면 반환, 없으면 None.`, `추출된 raw 텍스트를 LLM으로 깔끔한 Markdown으로 정리.`, `연속으로 동일한 셀 값을 하나로 축소.`, `Markdown 테이블에서 병합 셀로 인한 컬럼 중복을 제거.`, `단일 파일을 Docling으로 변환. 성공 시 True 반환.` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 3` to `Community 2`, `Community 6`?**
  _High betweenness centrality (0.326) - this node is a cross-community bridge._
- **Why does `env_or_dotenv()` connect `Community 6` to `Community 0`, `Community 3`?**
  _High betweenness centrality (0.320) - this node is a cross-community bridge._
- **Why does `RepairScriptTests` connect `Community 1` to `Community 6`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `main()` (e.g. with `env_or_dotenv()` and `parse_args()`) actually correct?**
  _`main()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pdftotext로 PDF 텍스트 레이어 추출. 텍스트가 있으면 반환, 없으면 None.`, `추출된 raw 텍스트를 LLM으로 깔끔한 Markdown으로 정리.`, `연속으로 동일한 셀 값을 하나로 축소.` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._