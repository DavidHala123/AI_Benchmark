#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="palletizer-benchmark"
MIN_PYTHON="3.10"
TARGET_PYTHON="3.11"

check_python() {
  local version_cmd=""
  if command -v python3 >/dev/null 2>&1; then
    version_cmd="python3"
  elif command -v python >/dev/null 2>&1; then
    version_cmd="python"
  fi

  if [[ -z "$version_cmd" ]]; then
    echo "Python was not found in PATH. The Conda environment will install Python ${TARGET_PYTHON}."
    return 0
  fi

  local detected_version
  detected_version="$($version_cmd -c 'import sys; print(str(sys.version_info[0]) + "." + str(sys.version_info[1]))')"
  if $version_cmd - <<PY
import sys
current = tuple(map(int, "$detected_version".split(".")))
minimum = tuple(map(int, "$MIN_PYTHON".split(".")))
raise SystemExit(0 if current >= minimum else 1)
PY
  then
    echo "Python ${detected_version} detected."
  else
    echo "Python ${detected_version} is older than required minimum ${MIN_PYTHON}."
    echo "The Conda environment will install Python ${TARGET_PYTHON}."
  fi
}

ensure_conda() {
  if command -v conda >/dev/null 2>&1; then
    return 0
  fi

  echo "Conda was not found. Attempting Miniconda installation..."

  local install_dir="${HOME}/miniconda3"
  local os_name
  os_name="$(uname -s)"
  local arch_name
  arch_name="$(uname -m)"
  local installer=""

  case "$os_name" in
    Linux)
      installer="Miniconda3-latest-Linux-x86_64.sh"
      ;;
    Darwin)
      if [[ "$arch_name" == "arm64" ]]; then
        installer="Miniconda3-latest-MacOSX-arm64.sh"
      else
        installer="Miniconda3-latest-MacOSX-x86_64.sh"
      fi
      ;;
    *)
      echo "Unsupported platform for automatic Conda installation: ${os_name}"
      return 1
      ;;
  esac

  local url="https://repo.anaconda.com/miniconda/${installer}"
  local tmp_installer
  tmp_installer="$(mktemp)"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$tmp_installer"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$tmp_installer" "$url"
  else
    echo "Neither curl nor wget is available, cannot download Miniconda."
    return 1
  fi

  bash "$tmp_installer" -b -p "$install_dir"
  rm -f "$tmp_installer"

  # shellcheck disable=SC1091
  source "$install_dir/etc/profile.d/conda.sh"
  export PATH="$install_dir/bin:$PATH"
}

resolve_conda() {
  if command -v conda >/dev/null 2>&1; then
    return 0
  fi

  if [[ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    export PATH="${HOME}/miniconda3/bin:$PATH"
  fi

  command -v conda >/dev/null 2>&1
}

echo "[1/5] Checking Python installation..."
check_python

echo "[2/5] Checking Conda / Anaconda installation..."
if ! resolve_conda; then
  ensure_conda
fi
resolve_conda

echo "[3/5] Creating or updating Conda environment ${ENV_NAME} with Python ${TARGET_PYTHON}..."
conda create -y -n "$ENV_NAME" python="$TARGET_PYTHON"

echo "[4/5] Installing Python dependencies..."
conda run -n "$ENV_NAME" python -m pip install --upgrade pip
conda run -n "$ENV_NAME" python -m pip install PyQt5 pytest

echo "[5/5] Installation finished."
echo "Environment ${ENV_NAME} is ready."
echo "Launch the app with:"
echo "conda run -n ${ENV_NAME} python App/main.py"

