#!/usr/bin/env bash
# setup.sh — LLM Wiki 원스톱 환경 셋업
#
# 사용법:
#   ./scripts/setup.sh          # 기본 설치 (PDF 지원)
#   ./scripts/setup.sh --full   # 전체 설치 (PDF + DOCX, XLSX, PPTX, 이미지, EPUB)
#   ./scripts/setup.sh --skip-python   # Python/marker 설치 생략 (QMD만 셋업)
#   ./scripts/setup.sh --skip-qmd      # QMD 셋업 생략
#   ./scripts/setup.sh --skip-models   # 모델 다운로드 생략 (빠른 셋업)
#
# 지원 플랫폼: macOS, Linux (Ubuntu/Debian, Fedora/RHEL), Windows (WSL/Git Bash/MSYS2)
#
# 설치 항목:
#   1. 시스템 의존성 (ffmpeg 등)
#   2. Python venv + marker-pdf + markitdown (비텍스트 파싱)
#   3. marker-pdf ML 모델 다운로드 (surya OCR/layout/table)
#   4. CLIProxyAPI (LLM 보정용 프록시 + OAuth 안내)
#   5. QMD 검색 엔진 (모델 다운로드 + collection 생성 + 인덱싱)
#   6. 디렉토리 구조 확인/생성
#   7. 설정 파일 확인 (Claude Code MCP, manifest, index)

set -euo pipefail

# ── OS 감지 ────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Darwin)          OS_TYPE="macos" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        OS_TYPE="wsl"
      else
        OS_TYPE="linux"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      OS_TYPE="windows"
      ;;
    *)
      OS_TYPE="unknown"
      ;;
  esac

  # Linux 패키지 매니저 감지
  PKG_MANAGER=""
  if [[ "$OS_TYPE" == "linux" || "$OS_TYPE" == "wsl" ]]; then
    if command -v apt-get &>/dev/null; then
      PKG_MANAGER="apt"
    elif command -v dnf &>/dev/null; then
      PKG_MANAGER="dnf"
    elif command -v yum &>/dev/null; then
      PKG_MANAGER="yum"
    elif command -v pacman &>/dev/null; then
      PKG_MANAGER="pacman"
    fi
  fi

  # Windows 패키지 매니저 감지
  if [[ "$OS_TYPE" == "windows" ]]; then
    if command -v winget &>/dev/null; then
      PKG_MANAGER="winget"
    elif command -v choco &>/dev/null; then
      PKG_MANAGER="choco"
    elif command -v scoop &>/dev/null; then
      PKG_MANAGER="scoop"
    fi
  fi
}

detect_os
echo "=== LLM Wiki 환경 셋업 (${OS_TYPE}) ==="

# ── 패키지 설치 헬퍼 ──────────────────────────────────
pkg_install() {
  local pkg="$1"
  local pkg_apt="${2:-$pkg}"
  local pkg_dnf="${3:-$pkg_apt}"

  case "$OS_TYPE" in
    macos)
      if command -v brew &>/dev/null; then
        brew install "$pkg" --quiet 2>/dev/null || brew install "$pkg"
      else
        echo "  [ERROR] Homebrew가 필요합니다: https://brew.sh"
        return 1
      fi
      ;;
    linux|wsl)
      case "$PKG_MANAGER" in
        apt)    sudo apt-get update -qq && sudo apt-get install -y "$pkg_apt" -qq ;;
        dnf)    sudo dnf install -y "$pkg_dnf" -q ;;
        yum)    sudo yum install -y "$pkg_dnf" -q ;;
        pacman) sudo pacman -S --noconfirm "$pkg_apt" ;;
        *)
          echo "  [ERROR] 패키지 매니저를 찾을 수 없습니다."
          return 1
          ;;
      esac
      ;;
    windows)
      case "$PKG_MANAGER" in
        winget) winget install --silent "$pkg" ;;
        choco)  choco install "$pkg" -y --no-progress ;;
        scoop)  scoop install "$pkg" ;;
        *)
          echo "  [ERROR] winget, choco, 또는 scoop이 필요합니다."
          return 1
          ;;
      esac
      ;;
  esac
}

# ── venv 경로 헬퍼 (Windows vs Unix) ──────────────────
venv_bin_dir() {
  if [[ "$OS_TYPE" == "windows" ]]; then
    echo "$VENV_DIR/Scripts"
  else
    echo "$VENV_DIR/bin"
  fi
}

venv_activate() {
  local bin_dir
  bin_dir="$(venv_bin_dir)"
  if [[ -f "$bin_dir/activate" ]]; then
    source "$bin_dir/activate"
  else
    echo "  [ERROR] venv activate를 찾을 수 없습니다: $bin_dir/activate"
    exit 1
  fi
}

venv_python() {
  local bin_dir
  bin_dir="$(venv_bin_dir)"
  if [[ -x "$bin_dir/python3" ]]; then
    echo "$bin_dir/python3"
  elif [[ -x "$bin_dir/python" ]]; then
    echo "$bin_dir/python"
  else
    echo "python3"
  fi
}

# ── marker 모델 캐시 경로 ─────────────────────────────
marker_cache_dir() {
  case "$OS_TYPE" in
    macos)           echo "${HOME}/Library/Caches/datalab/models" ;;
    windows)         echo "${LOCALAPPDATA:-$HOME/AppData/Local}/datalab/models/Cache" ;;
    *)               echo "${HOME}/.cache/datalab/models" ;;
  esac
}

# ── CLIProxyAPI 바이너리명 ────────────────────────────
cliproxy_binary_name() {
  if [[ "$OS_TYPE" == "windows" ]]; then
    echo "cli-proxy-api.exe"
  else
    echo "cli-proxy-api"
  fi
}

# ── Flags ──────────────────────────────────────────────
FULL=false
SKIP_PYTHON=false
SKIP_QMD=false
SKIP_MODELS=false

for arg in "$@"; do
  case "$arg" in
    --full)          FULL=true ;;
    --skip-python)   SKIP_PYTHON=true ;;
    --skip-qmd)      SKIP_QMD=true ;;
    --skip-models)   SKIP_MODELS=true ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
TOOLS_DIR="$REPO_ROOT/tools"

TOTAL_STEPS=7
STEP=0
next_step() { STEP=$((STEP + 1)); echo ""; echo "── ${STEP}/${TOTAL_STEPS} $1 ──"; }

# ── 1. 시스템 의존성 ──────────────────────────────────
next_step "시스템 의존성"

# ffmpeg (markitdown 오디오 변환에 필요)
if command -v ffmpeg &>/dev/null; then
  echo "  [OK] ffmpeg: $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
else
  echo "  [INSTALL] ffmpeg 설치 중..."
  if pkg_install ffmpeg ffmpeg ffmpeg; then
    echo "  [OK] ffmpeg 설치 완료"
  else
    echo "  [WARN] ffmpeg 수동 설치 필요: https://ffmpeg.org/download.html"
  fi
fi

# Node.js (QMD에 필요)
if command -v node &>/dev/null; then
  echo "  [OK] Node.js: $(node --version)"
else
  echo "  [INSTALL] Node.js 설치 중..."
  if [[ "$OS_TYPE" == "windows" ]]; then
    if pkg_install Node.js nodejs nodejs; then
      echo "  [OK] Node.js 설치 완료"
    else
      echo "  [WARN] Node.js 수동 설치 필요: https://nodejs.org"
    fi
  else
    if pkg_install node nodejs nodejs; then
      echo "  [OK] Node.js 설치 완료"
    else
      echo "  [WARN] Node.js 수동 설치 필요: https://nodejs.org"
    fi
  fi
fi

# curl 확인 (Windows에서 없을 수 있음)
if ! command -v curl &>/dev/null; then
  echo "  [INSTALL] curl 설치 중..."
  pkg_install curl curl curl || echo "  [WARN] curl 수동 설치 필요"
fi

# ── 2. Python + marker-pdf + markitdown ────────────────
if $SKIP_PYTHON; then
  next_step "Python (건너뜀: --skip-python)"
else
  next_step "Python + 파싱 도구"

  # Python 3.10+ 탐색
  PYTHON=""
  for candidate in python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" &>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  done
  # macOS Homebrew libexec 경로
  if [[ -z "$PYTHON" && "$OS_TYPE" == "macos" ]]; then
    for ver in 3.13 3.12 3.11 3.10; do
      bp="/opt/homebrew/opt/python@${ver}/libexec/bin/python3"
      if [[ -x "$bp" ]]; then
        PYTHON="$bp"
        break
      fi
    done
  fi
  # Windows: python3이 없을 수 있으므로 python도 탐색
  if [[ -z "$PYTHON" ]]; then
    if command -v python3 &>/dev/null; then
      PYTHON="python3"
    elif command -v python &>/dev/null; then
      PYTHON="python"
    fi
  fi

  # Python 버전 확인 → 3.10 미만이면 자동 설치
  NEED_INSTALL=false
  if [[ -z "$PYTHON" ]]; then
    NEED_INSTALL=true
  else
    MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')
    MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
    if [[ "$MAJOR" -lt 3 || "$MINOR" -lt 10 ]]; then
      NEED_INSTALL=true
      echo "  [INFO] 현재 Python: $($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') (3.10+ 필요)"
    fi
  fi

  if $NEED_INSTALL; then
    echo "  [INSTALL] Python 3.12 설치 중..."
    case "$OS_TYPE" in
      macos)
        if command -v brew &>/dev/null; then
          brew install python@3.12 --quiet 2>/dev/null || brew install python@3.12
        else
          echo "  [ERROR] Homebrew가 필요합니다: https://brew.sh"
          exit 1
        fi
        ;;
      linux|wsl)
        case "$PKG_MANAGER" in
          apt)
            sudo apt-get update -qq
            # deadsnakes PPA for Ubuntu (python3.12가 기본 제공되지 않는 경우)
            if ! apt-cache show python3.12 &>/dev/null; then
              sudo apt-get install -y software-properties-common -qq
              sudo add-apt-repository -y ppa:deadsnakes/ppa
              sudo apt-get update -qq
            fi
            sudo apt-get install -y python3.12 python3.12-venv python3.12-dev -qq
            ;;
          dnf)    sudo dnf install -y python3.12 python3.12-devel -q ;;
          yum)    sudo yum install -y python3.12 python3.12-devel -q ;;
          pacman) sudo pacman -S --noconfirm python ;;
          *)
            echo "  [ERROR] Python 3.12를 자동 설치할 수 없습니다."
            exit 1
            ;;
        esac
        ;;
      windows)
        if [[ "$PKG_MANAGER" == "winget" ]]; then
          winget install --silent Python.Python.3.12
        elif [[ "$PKG_MANAGER" == "choco" ]]; then
          choco install python312 -y --no-progress
        elif [[ "$PKG_MANAGER" == "scoop" ]]; then
          scoop install python
        else
          echo "  [ERROR] Python 3.12를 자동 설치할 수 없습니다."
          echo "    https://www.python.org/downloads/ 에서 다운로드하세요."
          exit 1
        fi
        ;;
    esac

    # 설치 후 재탐색
    PYTHON=""
    for candidate in python3.12 python3.13 python3.11 python3.10 python3 python; do
      if command -v "$candidate" &>/dev/null; then
        PY_MINOR=$($candidate -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
        PY_MAJOR=$($candidate -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo "0")
        if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
          PYTHON="$candidate"
          break
        fi
      fi
    done
    # macOS Homebrew fallback
    if [[ -z "$PYTHON" && "$OS_TYPE" == "macos" ]]; then
      bp="/opt/homebrew/opt/python@3.12/libexec/bin/python3"
      if [[ -x "$bp" ]]; then
        PYTHON="$bp"
      fi
    fi
    if [[ -z "$PYTHON" ]]; then
      echo "  [ERROR] Python 3.12 설치 후에도 찾을 수 없습니다."
      exit 1
    fi
    echo "  [OK] Python 3.12 설치 완료"
  fi

  PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  echo "  [OK] Python $PYTHON_VERSION ($PYTHON)"

  # venv
  if [[ -d "$VENV_DIR" ]]; then
    echo "  [OK] 기존 venv 발견"
  else
    echo "  [CREATE] venv 생성 중..."
    $PYTHON -m venv "$VENV_DIR"
  fi
  venv_activate
  "$(venv_python)" -m pip install --upgrade pip --quiet

  # marker-pdf
  if "$(venv_python)" -c "import marker" &>/dev/null; then
    INSTALLED_VERSION=$("$(venv_python)" -m pip show marker-pdf 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo "  [OK] marker-pdf v${INSTALLED_VERSION}"
  else
    echo "  [INSTALL] marker-pdf 설치 중..."
    if $FULL; then
      "$(venv_python)" -m pip install "marker-pdf[full]" --quiet
    else
      "$(venv_python)" -m pip install marker-pdf --quiet
    fi
    echo "  [OK] marker-pdf 설치 완료"
  fi

  # markitdown
  if "$(venv_python)" -c "import markitdown" &>/dev/null; then
    INSTALLED_VERSION=$("$(venv_python)" -m pip show markitdown 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo "  [OK] markitdown v${INSTALLED_VERSION}"
  else
    echo "  [INSTALL] markitdown 설치 중..."
    "$(venv_python)" -m pip install "markitdown[all]" --quiet
    echo "  [OK] markitdown 설치 완료"
  fi

  # marker_single CLI 확인
  MARKER_CLI="$(venv_bin_dir)/marker_single"
  if [[ "$OS_TYPE" == "windows" ]]; then
    MARKER_CLI="$(venv_bin_dir)/marker_single.exe"
  fi
  if [[ -f "$MARKER_CLI" ]]; then
    echo "  [OK] marker_single CLI"
  else
    echo "  [WARN] marker_single을 찾을 수 없습니다"
  fi
fi

# ── 3. marker-pdf ML 모델 다운로드 ────────────────────
if $SKIP_PYTHON || $SKIP_MODELS; then
  next_step "marker 모델 (건너뜀)"
else
  next_step "marker-pdf ML 모델 다운로드"

  MARKER_CACHE_DIR="$(marker_cache_dir)"

  if [[ -d "$MARKER_CACHE_DIR" ]] && [[ $(find "$MARKER_CACHE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ') -gt 5 ]]; then
    echo "  [OK] marker 모델 캐시 존재: $MARKER_CACHE_DIR"
  else
    echo "  [DOWNLOAD] surya OCR/layout/table 모델 다운로드 중..."
    echo "  (첫 실행 시 ~2GB 다운로드, 몇 분 소요)"
    if "$(venv_python)" -c "
from marker.models import create_model_dict
create_model_dict()
print('OK')
" 2>/dev/null | grep -q "OK"; then
      echo "  [OK] marker 모델 다운로드 완료"
    else
      echo "  [WARN] marker 모델 다운로드 실패. 첫 파싱 시 자동 다운로드됩니다."
    fi
  fi
fi

# ── 4. CLIProxyAPI ─────────────────────────────────────
if $SKIP_PYTHON; then
  next_step "CLIProxyAPI (건너뜀: --skip-python)"
else
  next_step "CLIProxyAPI (LLM 보정 프록시)"

  CLIPROXY_BIN_NAME="$(cliproxy_binary_name)"
  CLIPROXY_BIN="$TOOLS_DIR/$CLIPROXY_BIN_NAME"
  CLIPROXY_VERSION="v6.9.18"

  if [[ -f "$CLIPROXY_BIN" ]]; then
    echo "  [OK] CLIProxyAPI 이미 설치됨"
  else
    echo "  [INSTALL] CLIProxyAPI 다운로드 중 ($CLIPROXY_VERSION)..."
    mkdir -p "$TOOLS_DIR"

    DL_OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    DL_ARCH=$(uname -m)
    case "$DL_ARCH" in
      x86_64)        DL_ARCH="amd64" ;;
      aarch64|arm64) DL_ARCH="arm64" ;;
      i686|i386)     DL_ARCH="386" ;;
    esac

    # Windows 감지 (MINGW/MSYS에서 uname -s가 MINGW64_NT 등을 반환)
    if [[ "$OS_TYPE" == "windows" ]]; then
      DL_OS="windows"
    fi

    if [[ "$OS_TYPE" == "windows" ]]; then
      ARCHIVE="CLIProxyAPI_${CLIPROXY_VERSION#v}_${DL_OS}_${DL_ARCH}.zip"
    else
      ARCHIVE="CLIProxyAPI_${CLIPROXY_VERSION#v}_${DL_OS}_${DL_ARCH}.tar.gz"
    fi
    URL="https://github.com/router-for-me/CLIProxyAPI/releases/download/${CLIPROXY_VERSION}/${ARCHIVE}"

    TMPFILE="${TMPDIR:-/tmp}/$ARCHIVE"
    if curl -sL "$URL" -o "$TMPFILE"; then
      if [[ "$OS_TYPE" == "windows" ]]; then
        if command -v unzip &>/dev/null; then
          unzip -qo "$TMPFILE" -d "$TOOLS_DIR"
        elif command -v powershell &>/dev/null; then
          powershell -Command "Expand-Archive -Force '$TMPFILE' '$TOOLS_DIR'"
        fi
      else
        tar xzf "$TMPFILE" -C "$TOOLS_DIR"
        chmod +x "$CLIPROXY_BIN"
      fi
      rm -f "$TMPFILE"
      echo "  [OK] CLIProxyAPI 설치 완료"
    else
      echo "  [WARN] CLIProxyAPI 다운로드 실패. LLM 보정 없이 사용 가능합니다."
      echo "    수동 다운로드: $URL"
    fi
  fi

  # config.yaml
  CLIPROXY_CONFIG="$TOOLS_DIR/config.yaml"
  if [[ -f "$CLIPROXY_CONFIG" ]]; then
    echo "  [OK] config.yaml 존재"
  else
    cat > "$CLIPROXY_CONFIG" <<'YAML'
host: "127.0.0.1"
port: 8317

remote-management:
  allow-remote: false
  secret-key: ""

auth-dir: "~/.cli-proxy-api"

api-keys:
  - "marker-local"

debug: false
request-retry: 1
YAML
    echo "  [CREATE] config.yaml 생성"
  fi

  # Codex OAuth 로그인 상태 확인
  CLIPROXY_AUTH_DIR="${HOME}/.cli-proxy-api"
  if [[ -d "$CLIPROXY_AUTH_DIR" ]] && [[ -n "$(ls -A "$CLIPROXY_AUTH_DIR" 2>/dev/null)" ]]; then
    echo "  [OK] Codex OAuth 인증 정보 존재"
  else
    echo "  [ACTION] Codex OAuth 로그인이 필요합니다 (최초 1회):"
    if [[ "$OS_TYPE" == "windows" ]]; then
      echo "    cd tools && .\\cli-proxy-api.exe -codex-login"
    else
      echo "    cd tools && ./cli-proxy-api -codex-login"
    fi
  fi
fi

# ── 5. QMD 검색 엔진 ──────────────────────────────────
if $SKIP_QMD; then
  next_step "QMD (건너뜀: --skip-qmd)"
else
  next_step "QMD 검색 엔진"

  # qmd CLI 확인
  if ! command -v qmd &>/dev/null; then
    echo "  [INSTALL] qmd 설치 중 (npm)..."
    if command -v npm &>/dev/null; then
      npm install -g @tobilu/qmd --quiet 2>/dev/null || npm install -g @tobilu/qmd
      echo "  [OK] qmd 설치 완료"
    else
      echo "  [ERROR] npm이 설치되어 있지 않습니다. qmd를 설치할 수 없습니다."
      echo "    npm install -g @tobilu/qmd"
      SKIP_QMD=true
    fi
  else
    echo "  [OK] qmd CLI: $(command -v qmd)"
  fi

  if ! $SKIP_QMD; then
    # QMD 모델 다운로드 (embedding + reranking + generation, ~2GB)
    if $SKIP_MODELS; then
      echo "  [SKIP] QMD 모델 다운로드 (--skip-models)"
    else
      QMD_MODEL_DIR="${HOME}/.cache/qmd/models"
      if [[ "$OS_TYPE" == "windows" ]]; then
        QMD_MODEL_DIR="${LOCALAPPDATA:-$HOME/AppData/Local}/qmd/models"
      fi
      GGUF_COUNT=$(find "$QMD_MODEL_DIR" -name "*.gguf" -type f 2>/dev/null | wc -l | tr -d ' ')
      if [[ -d "$QMD_MODEL_DIR" ]] && [[ "$GGUF_COUNT" -ge 3 ]]; then
        echo "  [OK] QMD 모델 캐시 존재 (${GGUF_COUNT}/3 GGUF)"
      else
        echo "  [DOWNLOAD] QMD 모델 다운로드 중 (embedding + reranking + generation)..."
        echo "  (첫 실행 시 ~2GB 다운로드, 몇 분 소요)"
        qmd pull 2>&1 | sed 's/^/  /' || echo "  [WARN] QMD 모델 다운로드 실패. qmd pull로 수동 다운로드하세요."
      fi
    fi

    # wiki collection
    if qmd collection show wiki 2>/dev/null | grep -q "Path:"; then
      echo "  [OK] collection 'wiki' 존재"
    else
      echo "  [CREATE] collection 'wiki' 생성 중..."
      qmd collection add wiki "$REPO_ROOT/wiki"
      echo "  [OK] collection 'wiki' 생성 완료"
    fi

    # raw collection
    if qmd collection show raw 2>/dev/null | grep -q "Path:"; then
      echo "  [OK] collection 'raw' 존재"
    else
      echo "  [CREATE] collection 'raw' 생성 중..."
      qmd collection add raw "$REPO_ROOT/raw"
      echo "  [OK] collection 'raw' 생성 완료"
    fi

    # output collection
    if qmd collection show output 2>/dev/null | grep -q "Path:"; then
      echo "  [OK] collection 'output' 존재"
    else
      echo "  [CREATE] collection 'output' 생성 중..."
      qmd collection add output "$REPO_ROOT/output"
      echo "  [OK] collection 'output' 생성 완료"
    fi

    # 인덱싱 + 임베딩
    echo "  [INDEX] 인덱스 업데이트 중..."
    qmd update 2>/dev/null || true
    echo "  [EMBED] 벡터 임베딩 생성 중..."
    qmd embed 2>/dev/null || true
    echo "  [OK] QMD 검색 준비 완료"
  fi
fi

# ── 6. 디렉토리 구조 확인 ─────────────────────────────
next_step "디렉토리 구조"
DIRS=(
  "raw/meetings" "raw/briefs" "raw/slack" "raw/transcripts" "raw/links" "raw/files"
  "wiki/systems" "wiki/processes" "wiki/projects" "wiki/decisions"
  "wiki/playbooks" "wiki/entities" "wiki/glossary" "wiki/index" "wiki/_meta"
  "wiki/entities/brands" "wiki/entities/customers" "wiki/entities/data-sources"
  "wiki/entities/partners" "wiki/entities/systems"
  "output/briefs" "output/onboarding" "output/action-items" "output/reports"
  "templates" "prompts"
)

missing=0
for dir in "${DIRS[@]}"; do
  if [[ ! -d "$REPO_ROOT/$dir" ]]; then
    mkdir -p "$REPO_ROOT/$dir"
    echo "  [CREATE] $dir/"
    missing=$((missing + 1))
  fi
done
if [[ "$missing" -eq 0 ]]; then
  echo "  [OK] 디렉토리 구조 정상"
else
  echo "  [OK] ${missing}개 디렉토리 생성 완료"
fi

# ── 7. 설정 파일 확인 ─────────────────────────────────
next_step "최종 확인"

# parse-raw.sh 실행 권한 (Unix only)
if [[ "$OS_TYPE" != "windows" ]]; then
  if [[ -f "$SCRIPT_DIR/parse-raw.sh" ]] && [[ ! -x "$SCRIPT_DIR/parse-raw.sh" ]]; then
    chmod +x "$SCRIPT_DIR/parse-raw.sh"
    echo "  [FIX] parse-raw.sh 실행 권한 부여"
  else
    echo "  [OK] parse-raw.sh 실행 권한"
  fi
fi

# .claude/settings.json 확인
CLAUDE_SETTINGS="$REPO_ROOT/.claude/settings.json"
if [[ -f "$CLAUDE_SETTINGS" ]]; then
  if grep -q '"qmd"' "$CLAUDE_SETTINGS"; then
    echo "  [OK] Claude Code MCP 설정 (qmd)"
  else
    echo "  [WARN] .claude/settings.json에 qmd MCP 설정이 없습니다"
  fi
else
  echo "  [CREATE] .claude/settings.json 생성"
  mkdir -p "$REPO_ROOT/.claude"
  cat > "$CLAUDE_SETTINGS" <<'JSON'
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"],
      "env": {}
    }
  }
}
JSON
fi

# raw/.manifest.md 확인
if [[ -f "$REPO_ROOT/raw/.manifest.md" ]]; then
  echo "  [OK] raw/.manifest.md 존재"
else
  cat > "$REPO_ROOT/raw/.manifest.md" <<'MD'
# Raw Source Manifest

| 파일 | 유형 | 인제스트 상태 | 비고 |
|------|------|-------------|------|
MD
  echo "  [CREATE] raw/.manifest.md 생성"
fi

# wiki/index.md 확인
if [[ -f "$REPO_ROOT/wiki/index.md" ]]; then
  echo "  [OK] wiki/index.md 존재"
fi

# ── 완료 ───────────────────────────────────────────────
echo ""
echo "=== 셋업 완료 ($OS_TYPE) ==="
echo ""

if $FULL; then
  echo "설치 모드: full (PDF, DOCX, XLSX, PPTX, 이미지, EPUB)"
else
  echo "설치 모드: 기본 (PDF만)"
  echo "  전체 포맷 지원: ./scripts/setup.sh --full"
fi

echo ""
echo "다음 단계:"
if ! $SKIP_PYTHON; then
  if [[ "$OS_TYPE" == "windows" ]]; then
    echo "  .venv\\Scripts\\activate                       # venv 활성화"
    echo "  cd tools && .\\cli-proxy-api.exe -codex-login  # Codex OAuth 로그인 (최초 1회)"
    echo "  cd tools && start cli-proxy-api.exe            # CLIProxyAPI 서버 시작"
  else
    echo "  source .venv/bin/activate                    # venv 활성화"
    echo "  cd tools && ./cli-proxy-api -codex-login     # Codex OAuth 로그인 (최초 1회)"
    echo "  cd tools && ./cli-proxy-api &                # CLIProxyAPI 서버 시작"
  fi
fi
echo "  ./scripts/parse-raw.sh                       # raw/ 비텍스트 파일 파싱"
echo ""
echo "위키 운영:"
echo "  /project:catalog raw/meetings/파일.md         # raw 소스 등록"
echo "  /project:ingest raw/meetings/파일.md          # wiki로 승격"
echo "  /project:query 질문                           # 위키에 질문"
echo "  /project:lint                                # 건강검진"
