@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ENV_NAME=palletizer-benchmark"
set "MIN_PYTHON=3.10"
set "TARGET_PYTHON=3.11"
set "CONDA_EXE="

echo [1/5] Checking Python installation...
call :check_python
if errorlevel 1 exit /b 1

echo [2/5] Checking Conda / Anaconda installation...
call :ensure_conda
if errorlevel 1 exit /b 1

echo [3/5] Creating or updating Conda environment %ENV_NAME% with Python %TARGET_PYTHON%...
call "%CONDA_EXE%" create -y -n %ENV_NAME% python=%TARGET_PYTHON%
if errorlevel 1 exit /b 1

echo [4/5] Installing Python dependencies...
call "%CONDA_EXE%" run -n %ENV_NAME% python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
call "%CONDA_EXE%" run -n %ENV_NAME% python -m pip install PyQt5 pytest
if errorlevel 1 exit /b 1

echo [5/5] Installation finished.
echo Environment %ENV_NAME% is ready.
echo Launch the app with:
echo conda run -n %ENV_NAME% python App/main.py
exit /b 0

:check_python
set "CURRENT_PYTHON_VERSION="
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found in PATH. The project environment will install Python %TARGET_PYTHON% via Conda.
  exit /b 0
)

for /f "usebackq delims=" %%v in (`python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"`) do set "CURRENT_PYTHON_VERSION=%%v"
if not defined CURRENT_PYTHON_VERSION (
  echo Python exists but its version could not be detected.
  exit /b 1
)

powershell -NoProfile -Command "if ([version]'%CURRENT_PYTHON_VERSION%' -ge [version]'%MIN_PYTHON%') { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo Python %CURRENT_PYTHON_VERSION% is older than required minimum %MIN_PYTHON%.
  echo The project environment will install Python %TARGET_PYTHON% via Conda.
) else (
  echo Python %CURRENT_PYTHON_VERSION% detected.
)
exit /b 0

:ensure_conda
call :resolve_conda
if not errorlevel 1 (
  echo Conda detected at: %CONDA_EXE%
  exit /b 0
)

echo Conda was not found. Attempting Miniconda installation...
where winget >nul 2>nul
if not errorlevel 1 (
  echo Using winget to install Miniconda...
  winget install --id Anaconda.Miniconda3 -e --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo winget installation of Miniconda failed.
    exit /b 1
  )
) else (
  echo winget not available. Falling back to official Miniconda installer...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe'; $installer=Join-Path $env:TEMP 'Miniconda3-latest-Windows-x86_64.exe'; Invoke-WebRequest -Uri $url -OutFile $installer; Start-Process -FilePath $installer -ArgumentList '/InstallationType=JustMe','/RegisterPython=0','/S',('/D=' + $env:USERPROFILE + '\miniconda3') -Wait"
  if errorlevel 1 (
    echo Direct Miniconda installation failed.
    exit /b 1
  )
)

call :resolve_conda
if errorlevel 1 (
  echo Conda still could not be located after installation.
  exit /b 1
)

echo Conda installed successfully at: %CONDA_EXE%
exit /b 0

:resolve_conda
set "CONDA_EXE="
for /f "usebackq delims=" %%p in (`where conda 2^>nul`) do (
  set "CONDA_EXE=%%p"
  exit /b 0
)

for %%p in (
  "%UserProfile%\miniconda3\Scripts\conda.exe"
  "%UserProfile%\anaconda3\Scripts\conda.exe"
  "%ProgramData%\Miniconda3\Scripts\conda.exe"
  "%ProgramData%\Anaconda3\Scripts\conda.exe"
  "%ProgramFiles%\Miniconda3\Scripts\conda.exe"
  "%ProgramFiles%\Anaconda3\Scripts\conda.exe"
) do (
  if exist %%~p (
    set "CONDA_EXE=%%~p"
    exit /b 0
  )
)
exit /b 1
