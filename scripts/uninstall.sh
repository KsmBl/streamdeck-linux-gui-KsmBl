#!/usr/bin/env bash
#
# Removes a streamdeck-ui installation created by scripts/install.sh.
#
# Usage: scripts/uninstall.sh [--purge]
#
#   --purge   Also delete your configuration (~/.streamdeck_ui.json), its
#             backup, the log file and the cached application icons.
#
# Environment overrides:
#   PREFIX    Base prefix used at install time (default: ~/.local)

set -euo pipefail

PURGE=0
if [ "${1:-}" = "--purge" ]; then
    PURGE=1
fi

APP_NAME="streamdeck-ui"
PREFIX="${PREFIX:-$HOME/.local}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/$APP_NAME}"
BIN_DIR="$PREFIX/bin"
DESKTOP_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/512x512/apps"
UDEV_RULES_DEST="/etc/udev/rules.d/60-streamdeck.rules"

echo ">>> Stopping any running instance ..."
systemctl --user disable --now streamdeck.service 2>/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/streamdeck.service"
systemctl --user daemon-reload 2>/dev/null || true
pkill -f "$INSTALL_DIR/venv/bin/streamdeck" 2>/dev/null || true

echo ">>> Removing executables and virtual environment ..."
rm -f "$BIN_DIR/streamdeck" "$BIN_DIR/streamdeckc"
rm -rf "$INSTALL_DIR"

echo ">>> Removing application launcher and icon ..."
rm -f "$DESKTOP_DIR/$APP_NAME.desktop"
rm -f "$ICON_DIR/$APP_NAME.png"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ">>> Removing shell completions ..."
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/fish/completions/streamdeck.fish"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -f "$DATA_HOME/bash-completion/completions/streamdeck"
rm -f "$DATA_HOME/zsh/site-functions/_streamdeck"
if command -v fish >/dev/null 2>&1; then
    fish -c "set -q fish_user_paths; and set -U fish_user_paths (string match --invert -- '$BIN_DIR' \$fish_user_paths)" >/dev/null 2>&1 || true
fi

if [ -f "$UDEV_RULES_DEST" ]; then
    echo ">>> Removing udev rules from $UDEV_RULES_DEST (requires sudo)..."
    sudo rm -f "$UDEV_RULES_DEST"
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
fi

if [ "$PURGE" -eq 1 ]; then
    echo ">>> Purging configuration and cached data ..."
    rm -f "$HOME/.streamdeck_ui.json" "$HOME/.streamdeck_ui.json_old" "$HOME/.streamdeck_ui.log"
    rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/streamdeck_ui"
else
    echo ">>> Keeping your configuration (~/.streamdeck_ui.json). Use --purge to remove it."
fi

echo
echo "streamdeck-ui has been uninstalled."
echo "  - The 'input' group membership (if added) was left in place."
