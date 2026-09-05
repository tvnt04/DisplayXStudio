#!/bin/sh
set -eu
DATA_DIR="$HOME/Library/Application Support/Display X Studio"
APP_PATH="${1:-/Applications/Display X Studio.app}"
USER_APP_PATH="$HOME/Applications/Display X Studio.app"
osascript -e 'display dialog "This will remove Display X Studio and ALL of its saved data, including the license." buttons {"Cancel", "Uninstall"} default button "Uninstall" with icon caution'
rm -rf -- "$DATA_DIR"
rm -rf -- "$APP_PATH"
rm -rf -- "$USER_APP_PATH"
osascript -e 'display notification "Display X Studio and its saved data were removed." with title "Display X Studio"'
