@echo off
echo 🚀 Setting up Telegram & Slack Messenger App...

:: ✅ Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed. Please install Python 3 from https://www.python.org/
    pause
    exit /b 1
)

:: ✅ Create virtual environment if not exists
if not exist venv (
    echo 📦 Creating a virtual environment...
    python -m venv venv
)

:: ✅ Activate virtual environment
call venv\Scripts\activate.bat

:: ✅ Install dependencies
echo 📦 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: ✅ Run the app
echo 🚀 Running TelegramSlackApp...
python app.py

pause