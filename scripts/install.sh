#!/usr/bin/env bash
#
# Installs streamdeck-ui from this source checkout for the current user.
#
# It installs the package into a self-contained virtual environment, links the
# `streamdeck` / `streamdeckc` commands into ~/.local/bin, installs the udev
# rules required to talk to the device, and adds an application launcher entry.
#
# Usage: scripts/install.sh
#
# Environment overrides:
#   PREFIX   Base prefix for executables / desktop files (default: ~/.local)
#   PYTHON   Python interpreter to build the venv with     (default: python3)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_NAME="streamdeck-ui"
PYTHON="${PYTHON:-python3}"
PREFIX="${PREFIX:-$HOME/.local}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/$APP_NAME}"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$PREFIX/bin"
DESKTOP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/512x512/apps"
UDEV_RULES_SRC="$REPO_ROOT/udev/60-streamdeck.rules"
UDEV_RULES_DEST="/etc/udev/rules.d/60-streamdeck.rules"

echo ">>> Installing streamdeck-ui from: $REPO_ROOT"

# --- udev rules (needs root, so we ask for sudo) --------------------------
if [ -f "$UDEV_RULES_SRC" ]; then
    echo ">>> Installing udev rules to $UDEV_RULES_DEST (requires sudo)..."
    sudo install -Dm644 "$UDEV_RULES_SRC" "$UDEV_RULES_DEST"
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
else
    echo "WARNING: udev rules not found at $UDEV_RULES_SRC; skipping."
fi

# The "Press Keys" / "Write Text" features need access to /dev/uinput, which is
# granted via the 'input' group.
if ! id -nG "$USER" | grep -qw input; then
    echo ">>> Adding '$USER' to the 'input' group (log out and back in to apply)..."
    sudo usermod -aG input "$USER" || true
fi

# --- python package -------------------------------------------------------
echo ">>> Creating virtual environment at $VENV_DIR ..."
"$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
echo ">>> Installing the package and its dependencies (this can take a while)..."
"$VENV_DIR/bin/pip" install "$REPO_ROOT"

echo ">>> Linking executables into $BIN_DIR ..."
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/streamdeck" "$BIN_DIR/streamdeck"
ln -sf "$VENV_DIR/bin/streamdeckc" "$BIN_DIR/streamdeckc"

# --- desktop integration --------------------------------------------------
echo ">>> Installing application icon and launcher ..."
mkdir -p "$ICON_DIR" "$DESKTOP_DIR"
if [ -f "$REPO_ROOT/streamdeck_ui/logo.png" ]; then
    install -Dm644 "$REPO_ROOT/streamdeck_ui/logo.png" "$ICON_DIR/$APP_NAME.png"
fi
cat > "$DESKTOP_DIR/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Stream Deck UI
Comment=Configure and control your Elgato Stream Deck
Exec=$BIN_DIR/streamdeck
Icon=$APP_NAME
Terminal=false
Categories=Utility;
StartupNotify=false
EOF
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# --- shell completions ----------------------------------------------------
FISH_COMPLETION_SRC="$REPO_ROOT/completions/streamdeck.fish"
FISH_COMPLETION_DEST="${XDG_CONFIG_HOME:-$HOME/.config}/fish/completions/streamdeck.fish"
if command -v fish >/dev/null 2>&1 && [ -f "$FISH_COMPLETION_SRC" ]; then
    echo ">>> Installing fish shell completions ..."
    install -Dm644 "$FISH_COMPLETION_SRC" "$FISH_COMPLETION_DEST"
    # fish only autoloads a command's completions when the command is on PATH,
    # so make sure the bin directory is on fish's PATH.
    fish -c "fish_add_path -g '$BIN_DIR'" >/dev/null 2>&1 || true
fi

echo
echo "Installation complete!"
echo "  - Launch it from your application menu ('Stream Deck UI'), or run: streamdeck"
if ! printf '%s' ":$PATH:" | grep -q ":$BIN_DIR:"; then
    echo "  - NOTE: $BIN_DIR is not on your PATH. Add it, e.g.:"
    echo "        export PATH=\"$BIN_DIR:\$PATH\""
fi
echo "  - To uninstall, run: scripts/uninstall.sh"
