#!/bin/bash

set -e

APP_NAME="TelegramSlackApp"
APP_VERSION="1.0"
IDENTIFIER="com.yourname.TelegramSlackApp"

# 1. Clean previous builds
echo "🧹 Cleaning old build artifacts..."
rm -rf build dist pkg-root *.pkg *.plist

# 2. Build .app with py2app
echo "⚙️ Building .app with py2app..."
python3 setup.py py2app

# 3. Create pkg-root and move .app
echo "📦 Preparing pkg-root structure..."
mkdir -p pkg-root/Applications
cp -R "dist/$APP_NAME.app" pkg-root/Applications/

# 4. Create component.plist
echo "📝 Generating component.plist..."
pkgbuild --analyze --root pkg-root/Applications "$APP_NAME.plist"

# 5. Set BundleIsRelocatable to false
echo "🔒 Setting BundleIsRelocatable to false..."
/usr/libexec/PlistBuddy -c "Set :0:BundleIsRelocatable false" "$APP_NAME.plist"

# 6. Build .pkg installer
echo "📦 Creating .pkg installer..."
pkgbuild \
  --root pkg-root/Applications \
  --identifier "$IDENTIFIER" \
  --version "$APP_VERSION" \
  --install-location /Applications \
  --component-plist "$APP_NAME.plist" \
  "$APP_NAME.pkg"

echo "✅ Done! Installer created at ./$APP_NAME.pkg"
