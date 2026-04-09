#!/usr/bin/env bash
# parse-raw.sh — raw/ 내 비텍스트 파일을 파싱하여 .parsed.md를 생성한다.
#
# 라우팅:
#   PDF        → pdftotext (poppler)
#   그 외 파일  → MarkItDown (xlsx, docx, pptx, 이미지, html, epub 등)
#
# 사용법:
#   ./scripts/parse-raw.sh                               # raw/ 전체 스캔
#   ./scripts/parse-raw.sh raw/files/file.pdf             # 단일 파일 파싱
#
# 의존성:
#   PDF: poppler (pdftotext) — brew install poppler / apt install poppler-utils
#   그 외: pip install 'markitdown[all]'

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$REPO_ROOT/raw"
VENV_DIR="$REPO_ROOT/.venv"

# venv 자동 활성화 (markitdown용)
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
fi

# 지원 확장자
SUPPORTED_EXTS="pdf|pptx|docx|xlsx|xls|png|jpg|jpeg|gif|tiff|bmp|epub|html|csv|json|xml|wav|mp3"

parse_with_pdftotext() {
  local src="$1"
  local out="$2"

  if ! command -v pdftotext &>/dev/null; then
    echo "[ERROR] pdftotext가 설치되어 있지 않습니다."
    echo "  macOS: brew install poppler"
    echo "  Linux: apt install poppler-utils"
    return 1
  fi

  pdftotext "$src" "$out"
}

parse_with_markitdown() {
  local src="$1"
  local out="$2"

  if ! command -v markitdown &>/dev/null; then
    echo "[ERROR] markitdown이 설치되어 있지 않습니다."
    echo "  pip install 'markitdown[all]'"
    return 1
  fi

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
    else
      echo "[SKIP] 이미 파싱됨: $out"
      return 0
    fi
  fi

  echo "[PARSE] $src → $out"

  case "$ext" in
    pdf)
      echo "[ENGINE] pdftotext"
      parse_with_pdftotext "$src" "$out"
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
