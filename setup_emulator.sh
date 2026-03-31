#!/usr/bin/env bash
# One-time setup script for Android Emulator on macOS.
# Installs Android SDK command-line tools, system image, and creates an AVD.

set -euo pipefail

ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
AVD_NAME="redbot_pixel7"
SYSTEM_IMAGE="system-images;android-34;google_apis;x86_64"
DEVICE_PROFILE="pixel_7"

echo "============================================"
echo "  RedBot Android Emulator Setup (macOS)"
echo "============================================"
echo ""

# ── 1. Check for Java ──
if ! command -v java &>/dev/null; then
    echo "ERROR: Java is required. Install it with:"
    echo "  brew install openjdk"
    exit 1
fi

# ── 2. Install Android command-line tools if missing ──
if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
    echo "[1/6] Downloading Android command-line tools..."
    mkdir -p "$ANDROID_HOME"
    TOOLS_ZIP="/tmp/android-cmdline-tools.zip"

    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
    else
        TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip"
    fi

    curl -fsSL -o "$TOOLS_ZIP" "$TOOLS_URL"
    unzip -qo "$TOOLS_ZIP" -d "$ANDROID_HOME/cmdline-tools"
    mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
    rm -f "$TOOLS_ZIP"
    echo "  Installed to $ANDROID_HOME/cmdline-tools/latest"
else
    echo "[1/6] Android command-line tools already installed."
fi

export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# ── 3. Accept licenses ──
echo ""
echo "[2/6] Accepting SDK licenses..."
yes | sdkmanager --licenses >/dev/null 2>&1 || true

# ── 4. Install required SDK packages ──
echo ""
echo "[3/6] Installing SDK packages (platform-tools, emulator, system image)..."
sdkmanager --install \
    "platform-tools" \
    "emulator" \
    "platforms;android-34" \
    "$SYSTEM_IMAGE"

# ── 5. Create the AVD ──
echo ""
if "$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager" list avd 2>/dev/null | grep -q "$AVD_NAME"; then
    echo "[4/6] AVD '$AVD_NAME' already exists. Skipping creation."
else
    echo "[4/6] Creating AVD '$AVD_NAME' (Pixel 7, Android 14)..."
    echo "no" | avdmanager create avd \
        -n "$AVD_NAME" \
        -k "$SYSTEM_IMAGE" \
        -d "$DEVICE_PROFILE" \
        --force
    echo "  AVD created successfully."
fi

# ── 6. Tune AVD config for performance ──
AVD_CONFIG="$HOME/.android/avd/${AVD_NAME}.avd/config.ini"
if [ -f "$AVD_CONFIG" ]; then
    echo ""
    echo "[5/6] Tuning AVD performance settings..."
    # Set RAM, heap, and storage
    sed -i '' 's/^hw.ramSize=.*/hw.ramSize=4096/' "$AVD_CONFIG" 2>/dev/null || echo "hw.ramSize=4096" >> "$AVD_CONFIG"
    sed -i '' 's/^vm.heapSize=.*/vm.heapSize=512/' "$AVD_CONFIG" 2>/dev/null || echo "vm.heapSize=512" >> "$AVD_CONFIG"
    sed -i '' 's/^disk.dataPartition.size=.*/disk.dataPartition.size=8G/' "$AVD_CONFIG" 2>/dev/null || echo "disk.dataPartition.size=8G" >> "$AVD_CONFIG"
    echo "  RAM: 4096MB, Heap: 512MB, Storage: 8GB"
else
    echo "[5/6] AVD config not found at $AVD_CONFIG — skipping tuning."
fi

# ── 7. Check for Node.js + Appium ──
echo ""
echo "[6/6] Checking Appium setup..."
if ! command -v node &>/dev/null; then
    echo "  WARNING: Node.js not found. Install it with:"
    echo "    brew install node"
    echo "  Then install Appium:"
    echo "    npm install -g appium"
    echo "    appium driver install uiautomator2"
elif ! command -v appium &>/dev/null; then
    echo "  Node.js found. Installing Appium..."
    npm install -g appium
    appium driver install uiautomator2
    echo "  Appium installed successfully."
else
    echo "  Appium already installed."
    # Ensure UiAutomator2 driver is installed
    if ! appium driver list --installed 2>/dev/null | grep -q "uiautomator2"; then
        echo "  Installing UiAutomator2 driver..."
        appium driver install uiautomator2
    else
        echo "  UiAutomator2 driver already installed."
    fi
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "To verify, run:"
echo "  export ANDROID_HOME=$ANDROID_HOME"
echo "  export PATH=\$ANDROID_HOME/emulator:\$ANDROID_HOME/platform-tools:\$PATH"
echo "  emulator -avd $AVD_NAME -no-audio -gpu swiftshader_indirect"
echo ""
echo "Add these exports to your ~/.zshrc or ~/.bashrc for persistence."
echo ""
