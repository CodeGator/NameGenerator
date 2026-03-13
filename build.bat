@echo off
cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Create .venv or venv first, e.g.:
    echo   python -m venv .venv
    exit /b 1
)

pip install pyinstaller -r requirements.txt
pyinstaller NameGenerator.spec
