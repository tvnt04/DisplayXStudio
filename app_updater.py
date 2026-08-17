from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_current_appimage_path() -> Path:
    """Return the AppImage currently running this application."""

    if sys.platform != "linux":
        raise RuntimeError("AppImage updates are only supported on Linux.")

    try:
        path = Path(os.readlink("/proc/self/exe")).resolve()
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(
            "Could not determine the running AppImage path."
        ) from exc

    if not path.is_file() or path.suffix.lower() != ".appimage":
        raise RuntimeError(
            f"Current executable is not an AppImage: {path}"
        )

    return path


def install_appimage_update(downloaded_path: str | Path) -> None:
    """Replace the running AppImage using a system shell helper."""

    downloaded = Path(downloaded_path).resolve()

    if not downloaded.is_file():
        raise RuntimeError(
            f"Downloaded update does not exist: {downloaded}"
        )

    if downloaded.suffix.lower() != ".appimage":
        raise RuntimeError(
            f"Downloaded file is not an AppImage: {downloaded}"
        )

    current = get_current_appimage_path()

    if current == downloaded:
        raise RuntimeError(
            "The downloaded update is the currently running AppImage."
        )

    helper = Path(tempfile.gettempdir()) / "display-x-studio-updater.sh"
    log_file = Path(tempfile.gettempdir()) / "display-x-studio-updater.log"

    script = """#!/bin/sh
set -u

OLD="$1"
NEW="$2"
PID="$3"
LOG="$4"

exec >> "$LOG" 2>&1

echo "========================================"
echo "Display X Studio updater started"
echo "OLD=$OLD"
echo "NEW=$NEW"
echo "PID=$PID"
echo "========================================"

echo "Waiting for application PID $PID to exit..."

COUNT=0

while kill -0 "$PID" 2>/dev/null; do
    sleep 0.25
    COUNT=$((COUNT + 1))

    if [ "$COUNT" -ge 120 ]; then
        echo "ERROR: application did not exit within timeout."
        exit 1
    fi
done

echo "Application exited."

if [ ! -f "$OLD" ]; then
    echo "ERROR: old AppImage does not exist: $OLD"
    exit 1
fi

if [ ! -f "$NEW" ]; then
    echo "ERROR: downloaded AppImage does not exist: $NEW"
    exit 1
fi

BACKUP="${OLD}.backup"

echo "Creating backup: $BACKUP"

rm -f "$BACKUP"

if ! cp -p "$OLD" "$BACKUP"; then
    echo "ERROR: could not create backup."
    exit 1
fi

echo "Replacing old AppImage..."

if ! mv -f "$NEW" "$OLD"; then
    echo "ERROR: could not replace AppImage."

    if [ -f "$BACKUP" ]; then
        mv -f "$BACKUP" "$OLD"
    fi

    exit 1
fi

echo "Setting executable permission..."

chmod +x "$OLD"

if [ ! -x "$OLD" ]; then
    echo "ERROR: new AppImage is not executable."

    if [ -f "$BACKUP" ]; then
        mv -f "$BACKUP" "$OLD"
    fi

    exit 1
fi

rm -f "$BACKUP"

echo "Launching updated application..."

nohup "$OLD" >/dev/null 2>&1 &

echo "Update completed successfully."
exit 0
"""

    helper.write_text(script, encoding="utf-8")
    helper.chmod(0o700)

    subprocess.Popen(
        [
            "/bin/sh",
            str(helper),
            str(current),
            str(downloaded),
            str(os.getpid()),
            str(log_file),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    raise SystemExit(0)

