#!/usr/bin/env bash
# parse-raw.sh — raw/ 내 비텍스트 파일을 파싱하여 .parsed.md를 생성한다.
#
# 라우팅:
#   PDF        → Marker (CLIProxyAPI + gpt-5.4-mini LLM 보정)
#   그 외 파일  → MarkItDown (xlsx, docx, pptx, 이미지, html, epub 등)
#
# 사용법:
#   ./scripts/parse-raw.sh                               # raw/ 전체 스캔
#   ./scripts/parse-raw.sh raw/files/file.pdf             # 단일 파일 파싱
#   ./scripts/parse-raw.sh --no-llm raw/files/file.pdf    # PDF를 LLM 없이 파싱
#
# 의존성: pip install marker-pdf[full] 'markitdown[all]'
# LLM 모드 의존성: CLIProxyAPI (tools/cli-proxy-api)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$REPO_ROOT/raw"
VENV_DIR="$REPO_ROOT/.venv"

# LLM 설정 (CLIProxyAPI + gpt-5.4-mini, PDF 전용)
USE_LLM=true
OPENAI_MODEL="${MARKER_OPENAI_MODEL:-gpt-5.4-mini}"
OPENAI_BASE_URL="${MARKER_OPENAI_BASE_URL:-http://127.0.0.1:8317/v1}"
OPENAI_API_KEY="${MARKER_OPENAI_API_KEY:-marker-local}"
LLM_TIMEOUT="${MARKER_LLM_TIMEOUT:-300}"

# --no-llm 플래그 처리
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--no-llm" ]]; then
    USE_LLM=false
  else
    ARGS+=("$arg")
  fi
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

# venv 자동 활성화
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
elif ! command -v marker_single &>/dev/null || ! command -v markitdown &>/dev/null; then
  echo "[ERROR] marker_single 또는 markitdown을 찾을 수 없습니다."
  echo "  먼저 ./scripts/setup.sh --full 를 실행하세요."
  exit 1
fi

# 지원 확장자
SUPPORTED_EXTS="pdf|pptx|docx|xlsx|xls|png|jpg|jpeg|gif|tiff|bmp|epub|html|csv|json|xml|wav|mp3"

parse_with_marker() {
  local src="$1"
  local out="$2"
  local basename="${src%.*}"
  local marker_out_dir="${basename}"

  local llm_args=()
  if $USE_LLM; then
    llm_args=(
      --use_llm
      --llm_service marker.services.openai.OpenAIService
      --openai_base_url "$OPENAI_BASE_URL"
      --openai_api_key "$OPENAI_API_KEY"
      --openai_model "$OPENAI_MODEL"
      --config_json <(echo "{\"timeout\": $LLM_TIMEOUT}")
    )
    echo "[LLM] $OPENAI_MODEL via $OPENAI_BASE_URL"
  fi

  marker_single "$src" --output_format markdown --output_dir "$(dirname "$src")" "${llm_args[@]}"

  # marker 출력을 .parsed.md로 이동 + 이미지 경로 보정
  local marker_out_file
  marker_out_file=$(find "$marker_out_dir" -name "*.md" -type f 2>/dev/null | head -1)

  if [[ -n "$marker_out_file" ]]; then
    local dir_name
    dir_name=$(basename "$marker_out_dir")
    sed "s|!\[\([^]]*\)\](\([^/)][^)]*\))|![\1](${dir_name}/\2)|g" "$marker_out_file" > "$out"
    rm "$marker_out_file"

    # _meta.json 정리
    find "$marker_out_dir" -name "*_meta.json" -delete 2>/dev/null

    # 빈 디렉토리면 삭제, 이미지가 있으면 보존
    local file_count
    file_count=$(find "$marker_out_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$file_count" -eq 0 ]]; then
      rm -rf "$marker_out_dir"
    else
      echo "[INFO] 추출된 이미지 보존: $marker_out_dir/ (${file_count}개 파일)"
    fi
  else
    echo "[WARN] marker 출력을 찾을 수 없음: $src"
    return 1
  fi
}

parse_with_markitdown() {
  local src="$1"
  local out="$2"

  markitdown "$src" -o "$out"
}

parse_file() {
  local src="$1"
  local basename="${src%.*}"
  local out="${basename}.parsed.md"
  local ext="${src##*.}"
  ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

  # 이미 파싱된 파일 스킵 (원본이 새로우면 재파싱)
  if [[ -f "$out" ]]; then
    if [[ "$src" -nt "$out" ]]; then
      echo "[REPARSE] 원본이 갱신됨: $src"
      rm -f "$out"
      rm -rf "${basename}" 2>/dev/null
    else
      echo "[SKIP] 이미 파싱됨: $out"
      return 0
    fi
  fi

  echo "[PARSE] $src → $out"

  case "$ext" in
    pdf)
      echo "[ENGINE] Marker"
      parse_with_marker "$src" "$out"
      ;;
    *)
      echo "[ENGINE] MarkItDown"
      parse_with_markitdown "$src" "$out"
      ;;
  esac

  if [[ -f "$out" ]]; then
    echo "[DONE] $out"
  else
    echo "[WARN] 파싱 실패: $src"
    return 1
  fi
}

if [[ $# -ge 1 ]]; then
  parse_file "$1"
else
  echo "=== raw/ 비텍스트 파일 스캔 ==="
  found=0
  while IFS= read -r -d '' file; do
    parse_file "$file" || true
    found=$((found + 1))
  done < <(find "$RAW_DIR" -type f \( -iname "*.pdf" -o -iname "*.pptx" -o -iname "*.docx" -o -iname "*.xlsx" -o -iname "*.xls" \
             -o -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.tiff" \
             -o -iname "*.bmp" -o -iname "*.epub" -o -iname "*.html" -o -iname "*.csv" -o -iname "*.json" \
             -o -iname "*.xml" -o -iname "*.wav" -o -iname "*.mp3" \) -print0)

  if [[ "$found" -eq 0 ]]; then
    echo "파싱할 비텍스트 파일이 없습니다."
  else
    echo "=== 완료: ${found}개 파일 처리 ==="
  fi
fi
