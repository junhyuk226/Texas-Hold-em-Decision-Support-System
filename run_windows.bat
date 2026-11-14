@echo off
setlocal
cd /d "%~dp0"

rem Prefer the Python launcher; fall back to python on PATH.
set "PYTHON_CMD=py -3"
py -3 --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=python"
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Python 3.10 or later was not found.
        echo Install Python from https://www.python.org/downloads/windows/
        echo During installation, enable the option to add Python to PATH.
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Python 3.10 or later is required.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create the local virtual environment.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo The existing project .venv uses an unsupported Python version.
    echo Delete this project's .venv folder and run this script again.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip check
if errorlevel 1 (
    echo Dependency validation failed.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py
endlocal
