from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    """Start a helper process that replaces the running AppImage."""

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

    helper = Path(tempfile.gettempdir()) / (
        "display-x-studio-updater.py"
    )

    helper.write_text(
        """\
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

old_path = Path(sys.argv[1])
new_path = Path(sys.argv[2])
pid = int(sys.argv[3])

for _ in range(120):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        break
    except PermissionError:
        pass
    time.sleep(0.25)
else:
    sys.exit(1)

backup_path = old_path.with_suffix(old_path.suffix + ".backup")

try:
    if backup_path.exists():
        backup_path.unlink()

    shutil.copy2(old_path, backup_path)

    os.replace(new_path, old_path)

    old_path.chmod(
        old_path.stat().st_mode
        | 0o111
    )

    backup_path.unlink(missing_ok=True)

except Exception:
    try:
        if backup_path.exists():
            os.replace(backup_path, old_path)
    except Exception:
        pass
    sys.exit(1)

subprocess.Popen(
    [str(old_path)],
    start_new_session=True,
)
""",
        encoding="utf-8",
    )

    subprocess.Popen(
        [
            sys.executable,
            str(helper),
            str(current),
            str(downloaded),
            str(os.getpid()),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    raise SystemExit(0)
