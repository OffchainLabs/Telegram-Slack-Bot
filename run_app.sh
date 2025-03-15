#!/bin/bash

echo "🚀 Setting up Telegram & Slack Messenger App..."

# ✅ Check if Python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 is not installed. Installing now..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Install Python using Homebrew (macOS)
        if ! command -v brew &> /dev/null; then
            echo "⚠️ Homebrew is not installed. Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Install Python on Linux
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
    fi

    echo "✅ Python3 installed successfully!"
fi

# ✅ Create & activate virtual environment
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
