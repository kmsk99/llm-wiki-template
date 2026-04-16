#!/usr/bin/env bash
# parse-raw.sh — raw/ 내 비텍스트 파일을 하이브리드 파이프라인으로 파싱하여 .parsed.md를 생성한다.
#
# 엔진: opendataloader-pdf + Docling + CLIProxyAPI
#   - PDF → opendataloader-pdf (Java JAR) + CLIPROXY 이미지 캡션 (scripts/parse-pdf.py)
#   - HTML → scripts/parse-html.py (data.go.kr 본문 추출 전용)
#   - HWP/HWPX → scripts/parse-hwp.py
#   - 이미지 → scripts/parse-image.py (GPT Vision)
#   - TXT/DOC → scripts/parse-text.py
#   - 그 외 (XLSX, DOCX, PPTX 등) → Docling 통합 변환
#
# 사용법:
#   ./scripts/parse-raw.sh                               # raw/ 전체 스캔
#   ./scripts/parse-raw.sh raw/files/file.pdf             # 단일 파일 파싱
#   ./scripts/parse-raw.sh --no-llm raw/files/file.pdf    # LLM 없이 파싱
#   ./scripts/parse-raw.sh --no-ocr raw/files/file.pdf    # OCR 없이 파싱
#
# 의존성: pip install 'docling[ocrmac]' httpx
# LLM 모드 의존성: CLIProxyAPI (tools/cli-proxy-api)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
ENV_FILE="$REPO_ROOT/.env"
SCRIPT="$REPO_ROOT/scripts/parse_docling.py"
HTML_PARSER="$REPO_ROOT/scripts/parse-html.py"
IMAGE_PARSER="$REPO_ROOT/scripts/parse-image.py"
HWP_PARSER="$REPO_ROOT/scripts/parse-hwp.py"
TEXT_PARSER="$REPO_ROOT/scripts/parse-text.py"
PDF_PARSER="$REPO_ROOT/scripts/parse-pdf.py"
PYTHON_BIN="python3"

# LLM 토글 플래그 수집 (공통 옵션)
EXTRA_FLAGS=()

# 파일 유형 먼저 판별해서 Docling이 꼭 필요하지 않은 경로는 바로 라우팅
ARGS=()
HTML_FILE=""
IMAGE_FILE=""
HWP_FILE=""
TEXT_FILE=""
PDF_FILE=""
for arg in "$@"; do
  case "$arg" in
    --no-llm|--no-ocr|--hybrid|--no-hybrid)
      EXTRA_FLAGS+=("$arg")
      ;;
    --hybrid-port=*|--hybrid-url=*|--hybrid-device=*|--hybrid-startup-timeout=*)
      EXTRA_FLAGS+=("$arg")
      ;;
    *.pdf|*.PDF)
      PDF_FILE="$arg"
      ;;
    *.html|*.htm|*.HTML|*.HTM)
      HTML_FILE="$arg"
      ;;
    *.hwp|*.hwpx|*.HWP|*.HWPX)
      HWP_FILE="$arg"
      ;;
    *.txt|*.TXT|*.doc|*.DOC)
      TEXT_FILE="$arg"
      ;;
    *.png|*.jpg|*.jpeg|*.gif|*.bmp|*.tiff|*.PNG|*.JPG|*.JPEG|*.GIF|*.BMP|*.TIFF)
      IMAGE_FILE="$arg"
      ;;
    *)
      ARGS+=("$arg")
      ;;
  esac
done

# venv 자동 활성화 (HWP/HWPX, HTML 보조 의존성 포함)
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  source "$VENV_DIR/bin/activate"
  PYTHON_BIN="$VENV_DIR/bin/python"
elif [[ -n "$HWP_FILE" ]]; then
  echo "[ERROR] HWP/HWPX 파싱에는 프로젝트 가상환경이 필요합니다."
  echo "  먼저 ./scripts/setup.sh 를 실행하세요."
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -n "$PDF_FILE" ]]; then
  local_basename="${PDF_FILE%.*}"
  local_out="${local_basename}.parsed.md"
  echo "[ENGINE] parse-pdf.py (opendataloader-pdf + CLIPROXY)"
  "$PYTHON_BIN" "$PDF_PARSER" "$PDF_FILE" "$local_out" "${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}"
  exit $?
fi

if [[ -n "$HTML_FILE" ]]; then
  if [[ -x "$HTML_PARSER" ]] || "$PYTHON_BIN" -c "import bs4" &>/dev/null 2>&1; then
    local_basename="${HTML_FILE%.*}"
    local_out="${local_basename}.parsed.md"
    echo "[ENGINE] parse-html.py (data.go.kr 전용)"
    "$PYTHON_BIN" "$HTML_PARSER" "$HTML_FILE" "$local_out"
    exit $?
  fi
fi

if [[ -n "$IMAGE_FILE" ]]; then
  local_basename="${IMAGE_FILE%.*}"
  local_out="${local_basename}.parsed.md"
  echo "[ENGINE] parse-image.py (direct GPT vision)"
  "$PYTHON_BIN" "$IMAGE_PARSER" "$IMAGE_FILE" "$local_out"
  exit $?
fi

if [[ -n "$HWP_FILE" ]]; then
  local_basename="${HWP_FILE%.*}"
  local_out="${local_basename}.parsed.md"
  echo "[ENGINE] parse-hwp.py"
  "$PYTHON_BIN" "$HWP_PARSER" "$HWP_FILE" "$local_out"
  exit $?
fi

if [[ -n "$TEXT_FILE" ]]; then
  local_basename="${TEXT_FILE%.*}"
  local_out="${local_basename}.parsed.md"
  echo "[ENGINE] parse-text.py"
  "$PYTHON_BIN" "$TEXT_PARSER" "$TEXT_FILE" "$local_out"
  exit $?
fi
if ! "$PYTHON_BIN" -c "import docling" &>/dev/null; then
  echo "[ERROR] docling을 찾을 수 없습니다."
  echo "  먼저 ./scripts/setup.sh 를 실행하세요."
  exit 1
fi

# 환경변수 전달
export DOCLING_OPENAI_BASE_URL="${DOCLING_OPENAI_BASE_URL:-${MARKER_OPENAI_BASE_URL:-${CLIPROXY_BASE_URL:-http://127.0.0.1:8317/v1}}}"
export DOCLING_OPENAI_API_KEY="${DOCLING_OPENAI_API_KEY:-${MARKER_OPENAI_API_KEY:-${CLIPROXY_API_KEY:-marker-local}}}"
export DOCLING_OPENAI_MODEL="${DOCLING_OPENAI_MODEL:-${MARKER_OPENAI_MODEL:-gpt-5.4-mini}}"
export DOCLING_LLM_TIMEOUT="${DOCLING_LLM_TIMEOUT:-${MARKER_LLM_TIMEOUT:-300}}"

# 전체 스캔(인자 없음)일 때 PDF는 parse-pdf.py로 먼저 처리한 뒤 Docling에게 나머지를 넘긴다.
if [[ ${#ARGS[@]} -eq 0 ]]; then
  RAW_DIR="$REPO_ROOT/raw"
  if [[ -d "$RAW_DIR" ]]; then
    while IFS= read -r -d '' pdf; do
      pdf_basename="${pdf%.*}"
      pdf_out="${pdf_basename}.parsed.md"
      if [[ -f "$pdf_out" && "$pdf_out" -nt "$pdf" ]]; then
        continue
      fi
      echo "[SCAN] $pdf"
      "$PYTHON_BIN" "$PDF_PARSER" "$pdf" "$pdf_out" "${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}" || true
    done < <(find "$RAW_DIR" -type f \( -iname "*.pdf" \) -print0)
  fi
fi

exec "$PYTHON_BIN" "$SCRIPT" "${ARGS[@]+"${ARGS[@]}"}"
