#!/bin/bash

echo "🚀 Setting up Telegram & Slack Messenger App..."

# ✅ Step 1: Check if Python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 is not installed. Installing now..."
    
    # Install Python using Homebrew (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &> /dev/null; then
            echo "⚠️ Homebrew is not installed. Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python
    fi

    # Install Python using APT (Linux)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
    fi

    echo "✅ Python3 installed successfully!"
fi

# ✅ Step 2: Create & activate virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating a virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# ✅ Step 3: Install required dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ✅ Step 4: Run the app
echo "🚀 Running TelegramSlackApp..."
python app.py
