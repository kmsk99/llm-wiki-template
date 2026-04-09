#!/usr/bin/env bash
# setup.sh — LLM Wiki 초기 환경 셋업
#
# 사용법:
#   ./scripts/setup.sh          # 기본 설치 (PDF 지원)
#   ./scripts/setup.sh --full   # 전체 설치 (PDF + DOCX, XLSX, PPTX, 이미지, EPUB)
#
# .venv/ 가상환경을 프로젝트 루트에 생성하고 marker-pdf를 설치한다.
# tools/ 디렉토리에 CLIProxyAPI를 다운로드한다.

set -euo pipefail

FULL=false
if [[ "${1:-}" == "--full" ]]; then
  FULL=true
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
TOOLS_DIR="$REPO_ROOT/tools"

echo "=== LLM Wiki 환경 셋업 ==="

# 1. Python 3.10+ 탐색 (Homebrew 버전 우선, 시스템 python3 fallback)
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$candidate" &>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
# Homebrew libexec 경로도 탐색
if [[ -z "$PYTHON" ]]; then
  for ver in 3.13 3.12 3.11 3.10; do
    bp="/opt/homebrew/opt/python@${ver}/libexec/bin/python3"
    if [[ -x "$bp" ]]; then
      PYTHON="$bp"
      break
    fi
  done
fi
# 최종 fallback
if [[ -z "$PYTHON" ]]; then
  if command -v python3 &>/dev/null; then
    PYTHON="python3"
  else
    echo "[ERROR] python3이 설치되어 있지 않습니다."
    echo "  macOS: brew install python@3.12"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    exit 1
  fi
fi

PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Python $PYTHON_VERSION ($PYTHON)"

# Python 3.10+ 확인
MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')
if [[ "$MINOR" -lt 10 ]]; then
  echo "[ERROR] Python 3.10 이상이 필요합니다 (현재: $PYTHON_VERSION)"
  echo "  brew install python@3.12"
  exit 1
fi

# 2. venv 생성 또는 재사용
if [[ -d "$VENV_DIR" ]]; then
  echo "[OK] 기존 venv 발견: $VENV_DIR"
else
  echo "[CREATE] venv 생성 중: $VENV_DIR"
  $PYTHON -m venv "$VENV_DIR"
fi

# venv 활성화
source "$VENV_DIR/bin/activate"
echo "[OK] venv 활성화 ($(python3 --version))"

# 3. pip 업그레이드
python3 -m pip install --upgrade pip --quiet
echo "[OK] pip"

# 4. marker-pdf 설치
if python3 -c "import marker" &>/dev/null; then
  INSTALLED_VERSION=$(python3 -m pip show marker-pdf 2>/dev/null | grep "^Version:" | awk '{print $2}')
  echo "[OK] marker-pdf 이미 설치됨 (v${INSTALLED_VERSION})"
else
  echo "[INSTALL] marker-pdf 설치 중..."
  if $FULL; then
    python3 -m pip install "marker-pdf[full]"
  else
    python3 -m pip install marker-pdf
  fi
  echo "[OK] marker-pdf 설치 완료"
fi

# 4-2. markitdown 설치 (xlsx, docx, pptx 등 비PDF 파일용)
if python3 -c "import markitdown" &>/dev/null; then
  INSTALLED_VERSION=$(python3 -m pip show markitdown 2>/dev/null | grep "^Version:" | awk '{print $2}')
  echo "[OK] markitdown 이미 설치됨 (v${INSTALLED_VERSION})"
else
  echo "[INSTALL] markitdown 설치 중..."
  python3 -m pip install "markitdown[all]"
  echo "[OK] markitdown 설치 완료"
fi

# 5. marker_single CLI 확인
if [[ -x "$VENV_DIR/bin/marker_single" ]]; then
  echo "[OK] marker_single CLI: $VENV_DIR/bin/marker_single"
else
  echo "[WARN] marker_single을 찾을 수 없습니다."
fi

# 6. CLIProxyAPI 설치 (LLM 보정용)
CLIPROXY_BIN="$TOOLS_DIR/cli-proxy-api"
CLIPROXY_VERSION="v6.9.18"

if [[ -x "$CLIPROXY_BIN" ]]; then
  echo "[OK] CLIProxyAPI 이미 설치됨: $CLIPROXY_BIN"
else
  echo "[INSTALL] CLIProxyAPI 다운로드 중 ($CLIPROXY_VERSION)..."
  mkdir -p "$TOOLS_DIR"

  # OS/아키텍처 감지
  OS=$(uname -s | tr '[:upper:]' '[:lower:]')
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64)  ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
  esac

  TARBALL="CLIProxyAPI_${CLIPROXY_VERSION#v}_${OS}_${ARCH}.tar.gz"
  URL="https://github.com/router-for-me/CLIProxyAPI/releases/download/${CLIPROXY_VERSION}/${TARBALL}"

  if curl -sL "$URL" -o "/tmp/$TARBALL"; then
    tar xzf "/tmp/$TARBALL" -C "$TOOLS_DIR"
    rm -f "/tmp/$TARBALL"
    chmod +x "$CLIPROXY_BIN"
    echo "[OK] CLIProxyAPI 설치 완료: $CLIPROXY_BIN"
  else
    echo "[WARN] CLIProxyAPI 다운로드 실패. LLM 보정 없이 사용 가능합니다."
    echo "  수동 다운로드: $URL"
  fi
fi

# 7. CLIProxyAPI config 생성
CLIPROXY_CONFIG="$TOOLS_DIR/config.yaml"
if [[ -f "$CLIPROXY_CONFIG" ]]; then
  echo "[OK] CLIProxyAPI config 존재: $CLIPROXY_CONFIG"
else
  if [[ -f "$TOOLS_DIR/config.example.yaml" ]]; then
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
    echo "[CREATE] CLIProxyAPI config 생성: $CLIPROXY_CONFIG"
    echo "[INFO] Codex OAuth 로그인이 필요합니다:"
    echo "  cd tools && ./cli-proxy-api -codex-login"
  fi
fi

# 8. parse-raw.sh 실행 권한 확인
if [[ -x "$SCRIPT_DIR/parse-raw.sh" ]]; then
  echo "[OK] parse-raw.sh 실행 권한 확인"
else
  chmod +x "$SCRIPT_DIR/parse-raw.sh"
  echo "[FIX] parse-raw.sh 실행 권한 부여"
fi

# 9. 디렉토리 구조 확인
DIRS=("raw/meetings" "raw/briefs" "raw/slack" "raw/transcripts" "raw/links" "raw/files"
      "wiki/systems" "wiki/processes" "wiki/projects" "wiki/decisions"
      "wiki/playbooks" "wiki/entities" "wiki/glossary" "wiki/index" "wiki/_meta"
      "output/briefs" "output/onboarding" "output/action-items" "output/reports")

missing=0
for dir in "${DIRS[@]}"; do
  if [[ ! -d "$REPO_ROOT/$dir" ]]; then
    mkdir -p "$REPO_ROOT/$dir"
    echo "[CREATE] $dir/"
    missing=$((missing + 1))
  fi
done
if [[ "$missing" -eq 0 ]]; then
  echo "[OK] 디렉토리 구조 정상"
fi

echo ""
echo "=== 셋업 완료 ==="
if $FULL; then
  echo "설치 모드: full (PDF, DOCX, XLSX, PPTX, 이미지, EPUB)"
else
  echo "설치 모드: 기본 (PDF만)"
  echo "전체 포맷 지원이 필요하면: ./scripts/setup.sh --full"
fi
echo ""
echo "사용법:"
echo "  source .venv/bin/activate                    # venv 활성화"
echo "  cd tools && ./cli-proxy-api -codex-login     # Codex OAuth 로그인 (최초 1회)"
echo "  cd tools && ./cli-proxy-api &                # CLIProxyAPI 서버 시작"
echo "  ./scripts/parse-raw.sh                       # raw/ 전체 비텍스트 파일 파싱"
echo "  ./scripts/parse-raw.sh raw/files/file.pdf    # 단일 파일 파싱"
echo "  ./scripts/parse-raw.sh --no-llm raw/files/file.pdf  # LLM 없이 파싱"
