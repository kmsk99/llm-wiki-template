# Graph Report - /Users/mason/project/personal/llm-wiki-template  (2026-04-18)

## Corpus Check
- 11 files · ~15,781 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 168 nodes · 346 edges · 9 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.8)
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
- [[_COMMUNITY_Community 8|Community 8]]

## God Nodes (most connected - your core abstractions)
1. `upgrade_target()` - 24 edges
2. `TemplateUpgradeTests` - 13 edges
3. `UpgradeError` - 11 edges
4. `preflight_writes()` - 11 edges
5. `collapse_blank_lines()` - 10 edges
6. `repair_filename()` - 9 edges
7. `build_markdown()` - 9 edges
8. `sync_json_merge()` - 9 edges
9. `resolve_under()` - 8 edges
10. `parse_file()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `env_or_dotenv()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/parse_docling.py → /Users/mason/project/personal/llm-wiki-template/scripts/env_defaults.py
- `main()` --calls--> `parse_args()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/parse_docling.py → /Users/mason/project/personal/llm-wiki-template/scripts/parse-pdf.py
- `env_or_dotenv()` --calls--> `extract_hwpx_preview_image_text()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/env_defaults.py → /Users/mason/project/personal/llm-wiki-template/scripts/parse-hwp.py
- `main()` --calls--> `parse_args()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/template_upgrade.py → /Users/mason/project/personal/llm-wiki-template/scripts/parse-pdf.py
- `hash_file()` --calls--> `sha256()`  [INFERRED]
  /Users/mason/project/personal/llm-wiki-template/scripts/template_upgrade.py → /Users/mason/project/personal/llm-wiki-template/scripts/repair_parsed_artifacts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (41): sha256(), block_conflict_message(), build_lock_payload(), build_parser(), canonical_json(), copy_path(), current_block_hash(), deep_merge_preserve_existing() (+33 more)

### Community 1 - "Community 1"
Cohesion: 0.27
Nodes (18): build_markdown(), collapse_blank_lines(), extract_html_text(), extract_hwp_preview_text(), extract_hwp_text(), extract_hwp_text_hwp5txt(), extract_hwp_text_libhwp(), extract_hwpx_preview_image_text() (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (9): env_or_dotenv(), read_dotenv_value(), build_markdown(), main(), read_doc_file(), read_text_file(), EnvDefaultsTests, HwpParserTests (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.26
Nodes (14): canonical_duplicate(), cleaned_filename_hint(), display_path(), iter_raw_files(), looks_mojibake(), main(), needs_parse_refresh(), parse_args() (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.19
Nodes (16): build_data_url(), caption_image(), extract_message_text(), _find_hybrid_bin(), hybrid_server(), main(), mime_type_for(), parse_args() (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.2
Nodes (2): upgrade_target(), TemplateUpgradeTests

### Community 6 - "Community 6"
Cohesion: 0.2
Nodes (15): _build_ocr_options(), create_converter(), dedup_merged_cells(), _dedup_table_row(), _llm_format_markdown(), main(), parse_file(), _pdf_has_text_layer() (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.29
Nodes (12): build_data_url(), build_markdown(), call_gpt_vision(), extract_message_text(), get_tesseract_lang(), is_auth_error(), load_image_metadata(), main() (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.44
Nodes (10): best_node(), best_node_from_html(), candidate_score(), clean_node(), fallback_markdown(), iter_candidate_soups(), main(), meta_content() (+2 more)

## Knowledge Gaps
- **10 isolated node(s):** `pdftotext로 PDF 텍스트 레이어 추출. 텍스트가 있으면 반환, 없으면 None.`, `추출된 raw 텍스트를 LLM으로 깔끔한 Markdown으로 정리.`, `연속으로 동일한 셀 값을 하나로 축소.`, `Markdown 테이블에서 병합 셀로 인한 컬럼 중복을 제거.`, `단일 파일을 Docling으로 변환. 성공 시 True 반환.` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `parse_args()` connect `Community 4` to `Community 0`, `Community 6`?**
  _High betweenness centrality (0.307) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 6` to `Community 2`, `Community 4`?**
  _High betweenness centrality (0.299) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 0` to `Community 4`, `Community 5`?**
  _High betweenness centrality (0.248) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `upgrade_target()` (e.g. with `.test_dry_run_does_not_modify_target()` and `.test_apply_replaces_managed_paths_and_merges_settings()`) actually correct?**
  _`upgrade_target()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pdftotext로 PDF 텍스트 레이어 추출. 텍스트가 있으면 반환, 없으면 None.`, `추출된 raw 텍스트를 LLM으로 깔끔한 Markdown으로 정리.`, `연속으로 동일한 셀 값을 하나로 축소.` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._