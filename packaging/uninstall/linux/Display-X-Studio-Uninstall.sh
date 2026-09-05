#!/bin/sh
set -eu
DATA_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/Display X Studio"
if command -v zenity >/dev/null 2>&1; then
    zenity --question --title="Uninstall Display X Studio" --text="This will remove Display X Studio and ALL of its saved data, including the license.

Continue?" || exit 0
else
    printf "%s
" "This will remove Display X Studio and ALL of its saved data, including the license."
    printf "%s" "Type YES to continue: "
    read answer
    [ "$answer" = "YES" ] || exit 0
fi
rm -rf -- "$DATA_DIR"
