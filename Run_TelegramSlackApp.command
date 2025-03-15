#!/bin/bash

cd "$(dirname "$0")"  # ✅ Ensure script runs from the correct directory

echo "🚀 Detecting operating system..."

OS_TYPE=$(uname)

if [[ "$OS_TYPE" == "Darwin" || "$OS_TYPE" == "Linux" ]]; then
    echo "🖥️ Running on macOS/Linux..."
    ./run_app.sh  # ✅ Run the macOS/Linux script
else
    echo "🖥️ Running on Windows..."
    cmd.exe /c "run_app.bat"  # ✅ Run the Windows batch script
fi
