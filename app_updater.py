from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def get_current_appimage_path() -> Path:
    """Return the original AppImage file currently running this application."""

    if sys.platform != "linux":
        raise RuntimeError("AppImage updates are only supported on Linux.")

    appimage = os.environ.get("APPIMAGE")

    if appimage:
        path = Path(appimage).resolve()

        if path.is_file() and path.suffix.lower() == ".appimage":
            return path

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


def _start_detached(
    command: list[str],
    *,
    stdout=None,
    stderr=None,
) -> None:
    """Start a process independently of the current GUI process."""

    kwargs = {
        "start_new_session": True,
        "stdin": subprocess.DEVNULL,
        "stdout": stdout if stdout is not None else subprocess.DEVNULL,
        "stderr": stderr if stderr is not None else subprocess.DEVNULL,
    }

    if platform.system() == "Windows":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        )

    subprocess.Popen(command, **kwargs)


def install_appimage_update(downloaded_path: str | Path) -> None:
    """Replace the running AppImage using a detached shell helper."""

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
echo "Display X Studio AppImage updater started"
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

rm -f "$BACKUP"

echo "Creating backup: $BACKUP"

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

    _start_detached(
        [
            "/bin/sh",
            str(helper),
            str(current),
            str(downloaded),
            str(os.getpid()),
            str(log_file),
        ]
    )

    raise SystemExit(0)



def install_windows_installer_update(
    downloaded_path: str | Path,
) -> None:
    """Launch the Windows installer after the current app has fully exited."""

    if platform.system() != "Windows":
        raise RuntimeError(
            "Windows installer updates are only supported on Windows."
        )

    downloaded = Path(downloaded_path).resolve()

    if not downloaded.is_file():
        raise RuntimeError(
            f"Downloaded update does not exist: {downloaded}"
        )

    if downloaded.suffix.lower() != ".exe":
        raise RuntimeError(
            f"Downloaded update is not a Windows executable: {downloaded}"
        )

    helper = Path(tempfile.gettempdir()) / (
        "display-x-studio-installer-updater.ps1"
    )

    log_file = Path(tempfile.gettempdir()) / (
        "display-x-studio-installer-updater.log"
    )

    pid = os.getpid()

    script = r'''
param(
    [string]$Installer,
    [int]$Pid,
    [string]$LogFile
)

"========================================" | Out-File $LogFile -Append
"Display X Studio Windows installer updater" | Out-File $LogFile -Append
"INSTALLER=$Installer" | Out-File $LogFile -Append
"PID=$Pid" | Out-File $LogFile -Append
"========================================" | Out-File $LogFile -Append

"Waiting for Display X Studio to exit..." | Out-File $LogFile -Append

try {
    Wait-Process -Id $Pid -Timeout 60 -ErrorAction Stop
}
catch {
    # The process normally exits, so this is expected.
}

Start-Sleep -Seconds 2

if (-not (Test-Path $Installer)) {
    "ERROR: installer does not exist." | Out-File $LogFile -Append
    exit 1
}

"Starting installer..." | Out-File $LogFile -Append

try {
    Start-Process `
        -FilePath $Installer `
        -WorkingDirectory (Split-Path $Installer) `
        -ArgumentList "/CLOSEAPPLICATIONS"

    "Installer started successfully." | Out-File $LogFile -Append
}
catch {
    "ERROR: $($_.Exception.Message)" | Out-File $LogFile -Append
    exit 1
}
'''

    helper.write_text(script, encoding="utf-8")

    _start_detached(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper),
            "-Installer",
            str(downloaded),
            "-Pid",
            str(pid),
            "-LogFile",
            str(log_file),
        ]
    )

    raise SystemExit(0)

def install_windows_portable_update(downloaded_path: str | Path) -> None:
    """Replace a Windows portable installation using a detached helper."""

    if platform.system() != "Windows":
        raise RuntimeError(
            "Windows portable updates are only supported on Windows."
        )

    downloaded = Path(downloaded_path).resolve()

    if not downloaded.is_file():
        raise RuntimeError(
            f"Downloaded update does not exist: {downloaded}"
        )

    if downloaded.suffix.lower() != ".zip":
        raise RuntimeError(
            f"Downloaded update is not a ZIP file: {downloaded}"
        )

    current_executable = Path(sys.executable).resolve()
    install_dir = current_executable.parent

    helper = Path(tempfile.gettempdir()) / "display-x-studio-updater.py"
    log_file = Path(tempfile.gettempdir()) / "display-x-studio-updater.log"

    script = r'''
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path


def main() -> int:
    install_dir = Path(sys.argv[1]).resolve()
    downloaded = Path(sys.argv[2]).resolve()
    pid = int(sys.argv[3])
    log_file = Path(sys.argv[4]).resolve()

    with log_file.open("a", encoding="utf-8") as log:
        def write(message: str) -> None:
            log.write(message + "\n")
            log.flush()

        write("========================================")
        write("Display X Studio Windows portable updater")
        write(f"INSTALL_DIR={install_dir}")
        write(f"NEW={downloaded}")
        write(f"PID={pid}")
        write("========================================")

        for _ in range(120):
            try:
                os.kill(pid, 0)
            except OSError:
                break

            time.sleep(0.25)
        else:
            write("ERROR: application did not exit within timeout.")
            return 1

        if not downloaded.is_file():
            write(f"ERROR: downloaded ZIP does not exist: {downloaded}")
            return 1

        if not install_dir.is_dir():
            write(f"ERROR: installation directory does not exist: {install_dir}")
            return 1

        staging = Path(tempfile.mkdtemp(prefix="display-x-studio-update-"))

        try:
            write(f"Extracting update to {staging}")

            with zipfile.ZipFile(downloaded, "r") as archive:
                archive.extractall(staging)

            roots = list(staging.iterdir())

            if len(roots) == 1 and roots[0].is_dir():
                source_dir = roots[0]
            else:
                source_dir = staging

            backup = install_dir.with_name(
                install_dir.name + ".backup"
            )

            if backup.exists():
                shutil.rmtree(backup)

            write(f"Backing up installation to {backup}")
            os.replace(install_dir, backup)

            try:
                write(f"Installing new files into {install_dir}")
                os.replace(source_dir, install_dir)
            except Exception:
                if install_dir.exists():
                    shutil.rmtree(install_dir)

                os.replace(backup, install_dir)
                raise

            shutil.rmtree(backup, ignore_errors=True)
            write("Launching updated application")

            executable = install_dir / "Display X Studio.exe"

            if not executable.is_file():
                write(f"ERROR: executable not found: {executable}")
                return 1

            os.spawnv(
                os.P_NOWAIT,
                str(executable),
                [str(executable)],
            )

            write("Update completed successfully.")
            return 0

        except Exception as exc:
            write(f"ERROR: {exc}")
            return 1

        finally:
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
'''

    helper.write_text(script, encoding="utf-8")

    _start_detached(
        [
            sys.executable,
            str(helper),
            str(install_dir),
            str(downloaded),
            str(os.getpid()),
            str(log_file),
        ]
    )

    raise SystemExit(0)


def install_macos_dmg_update(downloaded_path: str | Path) -> None:
    """Replace the installed macOS application from a downloaded DMG."""

    if platform.system() != "Darwin":
        raise RuntimeError(
            "macOS DMG updates are only supported on macOS."
        )

    downloaded = Path(downloaded_path).resolve()

    if not downloaded.is_file():
        raise RuntimeError(
            f"Downloaded update does not exist: {downloaded}"
        )

    if downloaded.suffix.lower() != ".dmg":
        raise RuntimeError(
            f"Downloaded update is not a DMG: {downloaded}"
        )

    executable = Path(sys.executable).resolve()

    app_path = None

    for parent in executable.parents:
        if parent.suffix.lower() == ".app":
            app_path = parent
            break

    if app_path is None:
        raise RuntimeError(
            f"Could not determine installed .app path from {executable}"
        )

    helper = Path(tempfile.gettempdir()) / "display-x-studio-updater.py"
    log_file = Path(tempfile.gettempdir()) / "display-x-studio-updater.log"

    script = r'''
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    app_path = Path(sys.argv[1]).resolve()
    downloaded = Path(sys.argv[2]).resolve()
    pid = int(sys.argv[3])
    log_file = Path(sys.argv[4]).resolve()

    with log_file.open("a", encoding="utf-8") as log:
        def write(message: str) -> None:
            log.write(message + "\n")
            log.flush()

        write("========================================")
        write("Display X Studio macOS updater")
        write(f"APP={app_path}")
        write(f"DMG={downloaded}")
        write(f"PID={pid}")
        write("========================================")

        for _ in range(120):
            try:
                os.kill(pid, 0)
            except OSError:
                break

            time.sleep(0.25)
        else:
            write("ERROR: application did not exit within timeout.")
            return 1

        if not downloaded.is_file():
            write(f"ERROR: DMG does not exist: {downloaded}")
            return 1

        mount_point = Path(
            tempfile.mkdtemp(prefix="display-x-studio-dmg-")
        )

        backup = app_path.with_name(
            app_path.name + ".backup"
        )

        try:
            write(f"Mounting DMG at {mount_point}")

            result = subprocess.run(
                [
                    "hdiutil",
                    "attach",
                    str(downloaded),
                    "-nobrowse",
                    "-readonly",
                    "-mountpoint",
                    str(mount_point),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                write(result.stdout)
                write(result.stderr)
                return result.returncode

            apps = list(mount_point.glob("*.app"))

            if not apps:
                write("ERROR: no .app bundle found in DMG.")
                return 1

            source_app = apps[0]

            if backup.exists():
                shutil.rmtree(backup)

            write(f"Backing up {app_path} to {backup}")
            os.replace(app_path, backup)

            try:
                write(f"Copying {source_app} to {app_path}")

                shutil.copytree(
                    source_app,
                    app_path,
                )

            except Exception:
                if app_path.exists():
                    shutil.rmtree(app_path)

                os.replace(backup, app_path)
                raise

            shutil.rmtree(backup, ignore_errors=True)

            write("Unmounting DMG")

            subprocess.run(
                [
                    "hdiutil",
                    "detach",
                    str(mount_point),
                    "-force",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            write("Launching updated application")

            subprocess.Popen(
                ["open", str(app_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            write("Update completed successfully.")
            return 0

        except Exception as exc:
            write(f"ERROR: {exc}")
            return 1

        finally:
            subprocess.run(
                [
                    "hdiutil",
                    "detach",
                    str(mount_point),
                    "-force",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            shutil.rmtree(
                mount_point,
                ignore_errors=True,
            )


if __name__ == "__main__":
    raise SystemExit(main())
'''

    helper.write_text(script, encoding="utf-8")

    _start_detached(
        [
            sys.executable,
            str(helper),
            str(app_path),
            str(downloaded),
            str(os.getpid()),
            str(log_file),
        ]
    )

    raise SystemExit(0)
