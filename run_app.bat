@echo off
echo 🚀 Setting up Telegram & Slack Messenger App...

:: ✅ Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python3 is not installed. Please install Python3 manually.
    pause
    exit /b
)

:: ✅ Create virtual environment if not exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

:: ✅ Activate virtual environment
call venv\Scripts\activate

:: ✅ Install dependencies
echo 📦 Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

:: ✅ Run the app
echo 🚀 Running TelegramSlackApp...
python app.py
pause
