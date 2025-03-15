#!/bin/bash

echo "🚀 Setting up Telegram & Slack Messenger App..."

# ✅ Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 is not installed. Please install Python3 and try again."
    exit 1
fi

# ✅ Create & activate virtual environment (if not already)
if [ ! -d "venv" ]; then
    echo "📦 Creating a virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# ✅ Install required dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ✅ Run the app
echo "🚀 Running TelegramSlackApp..."
python app.py
