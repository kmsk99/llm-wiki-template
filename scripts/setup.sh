#!/usr/bin/env bash
# setup.sh — LLM Wiki 원스톱 환경 셋업
#
# 사용법:
#   ./scripts/setup.sh          # 기본 설치
#   ./scripts/setup.sh --skip-python   # 기존 Python/venv 환경을 그대로 사용
#
# 지원 플랫폼: macOS, Linux (Ubuntu/Debian, Fedora/RHEL), Windows (WSL/Git Bash/MSYS2)
#
# 설치 항목:
#   1. 시스템 의존성 (poppler, ffmpeg, tesseract, exiftool 등)
#   2. Python venv + Docling (비텍스트 파싱 — PDF, DOCX, PPTX, XLSX, 이미지 등)
#   3. Graphify 지식 그래프 도구
#   4. 디렉토리 구조 확인/생성
#   5. 설정 파일 확인 (Claude Code hooks, manifest, index)

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

# ── Flags ──────────────────────────────────────────────
SKIP_PYTHON=false

for arg in "$@"; do
  case "$arg" in
    --skip-python)   SKIP_PYTHON=true ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

TOTAL_STEPS=5
STEP=0
next_step() { STEP=$((STEP + 1)); echo ""; echo "── ${STEP}/${TOTAL_STEPS} $1 ──"; }

# ── 1. 시스템 의존성 ──────────────────────────────────
next_step "시스템 의존성"

# poppler (pdftotext — PDF 파싱에 필요)
if command -v pdftotext &>/dev/null; then
  echo "  [OK] pdftotext (poppler): $(pdftotext -v 2>&1 | head -1)"
else
  echo "  [INSTALL] poppler 설치 중..."
  if pkg_install poppler poppler-utils poppler-utils; then
    echo "  [OK] poppler 설치 완료"
  else
    echo "  [WARN] poppler 수동 설치 필요"
    echo "    macOS: brew install poppler"
    echo "    Linux: apt install poppler-utils"
  fi
fi

# ffmpeg (오디오 변환에 필요)
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

# tesseract (이미지 OCR에 필요)
if command -v tesseract &>/dev/null; then
  echo "  [OK] tesseract: $(tesseract --version 2>&1 | head -1 | awk '{print $2}')"
else
  echo "  [INSTALL] tesseract 설치 중..."
  if pkg_install tesseract tesseract tesseract-ocr; then
    echo "  [OK] tesseract 설치 완료"
  else
    echo "  [WARN] tesseract 수동 설치 필요"
    echo "    macOS: brew install tesseract tesseract-lang"
    echo "    Linux: apt install tesseract-ocr tesseract-ocr-kor"
  fi
fi

# exiftool (이미지/오디오 메타데이터 추출에 유용)
if command -v exiftool &>/dev/null; then
  echo "  [OK] exiftool: $(exiftool -ver)"
else
  echo "  [INSTALL] exiftool 설치 중..."
  if pkg_install exiftool libimage-exiftool-perl exiftool; then
    echo "  [OK] exiftool 설치 완료"
  else
    echo "  [WARN] exiftool 수동 설치 필요"
    echo "    macOS: brew install exiftool"
    echo "    Linux: apt install libimage-exiftool-perl"
  fi
fi

# curl 확인 (Windows에서 없을 수 있음)
if ! command -v curl &>/dev/null; then
  echo "  [INSTALL] curl 설치 중..."
  pkg_install curl curl curl || echo "  [WARN] curl 수동 설치 필요"
fi

# ── 2. Python + Docling ──────────────────────────────
if $SKIP_PYTHON; then
  next_step "Python (건너뜀: --skip-python)"
else
  next_step "Python + Docling"

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

  # Docling (DOCX, PPTX, XLSX, 이미지 등 통합 변환 — PDF는 opendataloader-pdf가 전담)
  if "$(venv_python)" -c "import docling" &>/dev/null; then
    INSTALLED_VERSION=$("$(venv_python)" -m pip show docling 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo "  [OK] docling v${INSTALLED_VERSION}"
  else
    echo "  [INSTALL] docling 설치 중..."
    if [[ "$OS_TYPE" == "macos" ]]; then
      "$(venv_python)" -m pip install "docling[ocrmac]" --quiet
    else
      "$(venv_python)" -m pip install docling --quiet
    fi
    echo "  [OK] docling 설치 완료"
  fi

  # Java 11+ 확인 (opendataloader-pdf JAR 실행용)
  if command -v java &>/dev/null; then
    JAVA_MAJOR=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | awk -F '.' '{print ($1=="1" ? $2 : $1)}')
    if [[ -n "$JAVA_MAJOR" && "$JAVA_MAJOR" =~ ^[0-9]+$ && "$JAVA_MAJOR" -ge 11 ]]; then
      echo "  [OK] Java ${JAVA_MAJOR}"
    else
      echo "  [WARN] Java 11+ 필요 (현재: $(java -version 2>&1 | head -1))"
    fi
  else
    echo "  [INSTALL] Java (Temurin 21) 설치 중..."
    case "$OS_TYPE" in
      macos)
        brew install --cask temurin --quiet 2>/dev/null || brew install --cask temurin || echo "  [WARN] Java 수동 설치 필요: https://adoptium.net"
        ;;
      linux|wsl)
        case "$PKG_MANAGER" in
          apt)    sudo apt-get install -y default-jre -qq ;;
          dnf)    sudo dnf install -y java-21-openjdk -q ;;
          yum)    sudo yum install -y java-21-openjdk -q ;;
          pacman) sudo pacman -S --noconfirm jre-openjdk ;;
          *)      echo "  [WARN] Java 수동 설치 필요: https://adoptium.net" ;;
        esac
        ;;
      windows)
        case "$PKG_MANAGER" in
          winget) winget install --silent EclipseAdoptium.Temurin.21.JRE ;;
          choco)  choco install temurin21 -y --no-progress ;;
          scoop)  scoop install temurin21-jre ;;
          *)      echo "  [WARN] Java 수동 설치 필요: https://adoptium.net" ;;
        esac
        ;;
    esac
  fi

  # opendataloader-pdf[hybrid] (PDF 전용 — Java JAR + Docling 하이브리드 수식 서버)
  HYBRID_READY=true
  for dep in fastapi uvicorn; do
    if ! "$(venv_python)" -c "import $dep" &>/dev/null; then
      HYBRID_READY=false
      break
    fi
  done
  if "$(venv_python)" -m pip show opendataloader-pdf &>/dev/null && $HYBRID_READY; then
    ODL_VERSION=$("$(venv_python)" -m pip show opendataloader-pdf 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo "  [OK] opendataloader-pdf v${ODL_VERSION} (hybrid ready)"
  else
    echo "  [INSTALL] opendataloader-pdf[hybrid] 설치 중 (수식 LaTeX 추출용)..."
    "$(venv_python)" -m pip install "opendataloader-pdf[hybrid]" --quiet
    echo "  [OK] opendataloader-pdf[hybrid] 설치 완료"
  fi

  # httpx (LLM 후처리용)
  if ! "$(venv_python)" -c "import httpx" &>/dev/null; then
    "$(venv_python)" -m pip install httpx --quiet
    echo "  [OK] httpx 설치 완료"
  else
    echo "  [OK] httpx"
  fi

  # HTML/HWP 보조 파서 의존성
  EXTRA_PY_PKGS=(beautifulsoup4 markdownify olefile)
  for pkg in "${EXTRA_PY_PKGS[@]}"; do
    if ! "$(venv_python)" -m pip show "$pkg" &>/dev/null; then
      "$(venv_python)" -m pip install "$pkg" --quiet
      echo "  [OK] $pkg 설치 완료"
    else
      echo "  [OK] $pkg"
    fi
  done
fi

# ── 3. Graphify ───────────────────────────────────────
if $SKIP_PYTHON; then
  next_step "Graphify (건너뜀: --skip-python)"
else
  next_step "Graphify 지식 그래프"

  if "$(venv_python)" -m pip show graphifyy &>/dev/null; then
    GRAPHIFY_VERSION=$("$(venv_python)" -m pip show graphifyy 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo "  [OK] graphifyy v${GRAPHIFY_VERSION}"
  else
    echo "  [INSTALL] graphifyy[mcp] 설치 중..."
    "$(venv_python)" -m pip install "graphifyy[mcp]" --quiet
    echo "  [OK] graphifyy 설치 완료"
  fi
fi

# ── 4. 디렉토리 구조 확인 ─────────────────────────────
next_step "디렉토리 구조"
DIRS=(
  "raw"
  "wiki" "wiki/_meta"
  "output"
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

# ── 5. 설정 파일 확인 ─────────────────────────────────
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
  if grep -q 'graphify' "$CLAUDE_SETTINGS"; then
    echo "  [OK] Claude Code hook 설정 (graphify)"
  else
    echo "  [WARN] .claude/settings.json에 graphify hook 설정이 없습니다"
  fi
else
  echo "  [CREATE] .claude/settings.json 생성"
  mkdir -p "$REPO_ROOT/.claude"
  cat > "$CLAUDE_SETTINGS" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Glob|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "[ -f graphify-out/graph.json ] && echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files."}}' || true"
          }
        ]
      }
    ]
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

모든 raw 소스의 목록과 인제스트 상태를 추적한다.

## 소스 목록

| 파일 | 유형 | 날짜 | 인제스트 상태 | 비고 |
|------|------|------|---------------|------|

<!-- 인제스트 상태: 완료 | 미정 | 부분 | 보류 -->
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
echo "다음 단계:"
echo "  ./scripts/parse-raw.sh                       # raw/ 비텍스트 파일 파싱"
echo ""
echo "위키 운영:"
echo "  /project:catalog raw/파일.md                  # raw 소스 등록"
echo "  /project:ingest raw/파일.md                   # wiki로 승격"
echo "  /project:query 질문                           # 위키에 질문"
echo "  /project:lint                                # 건강검진"

echo "  graphify . --update                          # 그래프 갱신"
