@echo off
chcp 65001 >nul
echo NHS Intelligent Alert System - Production Startup
echo ================================================

echo Checking Environment...
if not exist ".env" (
    echo Configuration file not found
    echo Creating configuration template...
    if exist "whatsapp_simple_config.env" (
        copy whatsapp_simple_config.env .env
        echo Created .env configuration file
    ) else (
        echo # NHS Intelligent Alert System Configuration > .env
        echo. >> .env
        echo # WhatsApp API Configuration >> .env
        echo WHATSAPP_ACCESS_TOKEN= >> .env
        echo WHATSAPP_PHONE_NUMBER_ID= >> .env
        echo WHATSAPP_WEBHOOK_URL=https://your-domain.com/webhook >> .env
        echo WHATSAPP_BUSINESS_NAME=NHS Waiting List Alert Service >> .env
        echo. >> .env
        echo # Database Configuration >> .env
        echo DATABASE_URL=sqlite:///nhs_alerts.db >> .env
        echo. >> .env
        echo # System Configuration >> .env
        echo API_PORT=8001 >> .env
        echo LOG_LEVEL=INFO >> .env
        echo Created basic configuration file
    )
    echo.
    echo Please edit .env file and fill in your configuration:
    echo    1. WHATSAPP_ACCESS_TOKEN
    echo    2. WHATSAPP_PHONE_NUMBER_ID  
    echo    3. WHATSAPP_WEBHOOK_URL
    echo    4. WHATSAPP_BUSINESS_NAME
    echo.
    echo Then run this script again
    pause
    exit /b 1
)

echo Configuration file found

echo Checking virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found
    echo Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing/Updating dependencies...
pip install -q -r requirements.txt
pip install -q aiohttp aiofiles python-dotenv

echo Initializing database...
if not exist "nhs_alerts.db" (
    echo Creating database...
    python -c "import sqlite3; import os; from database_init import init_database; init_database()" 2>nul || (
        echo Creating database with SQL script...
        sqlite3 nhs_alerts.db < create_db.sql
    )
)

echo Starting NHS Intelligent Alert System...
echo ================================================
echo Features Include:
echo    • Web Interface: http://localhost:8001
echo    • WhatsApp Intelligent Chat
echo    • 8 Types of Smart Alerts  
echo    • GP Appointment Monitoring
echo    • Real-time NHS Data ETL
echo ================================================

echo Press Ctrl+C to stop system
echo ================================================

python main.py

echo.
echo System stopped
pause 