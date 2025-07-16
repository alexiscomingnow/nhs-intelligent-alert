@echo off
chcp 65001 >nul
echo NHS Intelligent Alert System - Multilingual Version
echo ====================================================
echo Starting production environment...
echo ====================================================

echo Checking environment configuration...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if configuration file exists
if not exist ".env" (
    echo ERROR: Configuration file .env not found
    echo.
    echo Please run setup.bat first to create configuration file
    echo Or manually create .env file with required settings
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Virtual environment creation failed
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing/updating dependencies...
pip install -q -r requirements.txt
pip install -q aiohttp aiofiles python-dotenv beautifulsoup4 requests

echo Initializing database...
if not exist "nhs_alerts.db" (
    echo Creating database...
    python -c "import sqlite3; conn = sqlite3.connect('nhs_alerts.db'); conn.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)'); conn.close()" 2>nul
    if exist "create_db.sql" (
        echo Executing database initialization script...
        python -c "import sqlite3; conn = sqlite3.connect('nhs_alerts.db'); conn.executescript(open('create_db.sql', 'r', encoding='utf-8').read()); conn.close()" 2>nul
    )
)

echo Database initialization completed

echo.
echo Starting NHS Intelligent Alert System (Multilingual Version)...
echo ====================================================
echo Supported Languages:
echo    1. English (GB)
echo    2. Chinese (CN)
echo    3. Hindi (IN)
echo    4. Urdu (PK)
echo    5. Bengali (BD)
echo    6. Arabic (SA)
echo    7. Polish (PL)
echo    8. French (FR)
echo    9. Spanish (ES)
echo    10. Portuguese (PT)
echo ====================================================
echo Features include:
echo    • Multilingual Telegram Bot Interface
echo    • NHS Waiting Time Intelligent Alerts
echo    • User Preference Management
echo    • Real-time Data Monitoring
echo ====================================================
echo.
echo Usage Instructions:
echo    1. Search for your Bot in Telegram
echo    2. Send any message to start using
echo    3. Select your language preference
echo    4. Follow prompts to complete setup
echo.
echo Press Ctrl+C to stop system
echo ====================================================

python main.py

echo.
echo System stopped
pause 