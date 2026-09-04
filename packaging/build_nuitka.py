from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "main.py"


def get_version() -> str:
    text = (ROOT / "app_version.py").read_text(encoding="utf-8")
    match = re.search(
        r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']',
        text,
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError("Could not find APP_VERSION")
    return match.group(1)


def main() -> int:
    version = get_version()

    # Windows PE version resources require numeric dotted versions.
    # Keep the full APP_VERSION for the application/release metadata,
    # but normalize prerelease versions for Nuitka's Windows fields.
    windows_version = version.split("-", 1)[0].split("+", 1)[0]
    if sys.platform == "win32":
        parts = windows_version.split(".")
        if len(parts) < 4:
            windows_version = ".".join(parts + ["0"] * (4 - len(parts)))
        elif len(parts) > 4:
            windows_version = ".".join(parts[:4])

    if not ENTRY.is_file():
        raise SystemExit(f"Application entry point not found: {ENTRY}")

    dist = ROOT / "dist"

    if dist.exists():
        shutil.rmtree(dist)

    dist.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyqt5",
        f"--output-dir={dist}",
        "--include-data-file=logo.png=logo.png",
        "--include-data-file=logo_icon.png=logo_icon.png",
        str(ENTRY),
    ]

    if sys.platform == "win32":
        cmd += [
            "--windows-console-mode=disable",
            f"--windows-icon-from-ico={ROOT / 'logo.ico'}",
            "--windows-product-name=Display X Studio",
            "--windows-file-description=Display X Studio",
            f"--windows-file-version={windows_version}",
            f"--windows-product-version={windows_version}",
        ]

    elif sys.platform == "darwin":
        cmd += [
            "--macos-create-app-bundle",
            f"--macos-app-version={version}",
        ]

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    print("Building with Nuitka:")
    print(" ".join(cmd))

    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

    # Normalize Nuitka output to the directory/file names
    # expected by the existing packaging pipeline.

    if sys.platform == "win32":
        source = dist / "main.dist"
        target = dist / "Display X Studio"

        if target.exists():
            shutil.rmtree(target)

        source.rename(target)

        exe = target / "main.exe"
        target_exe = target / "Display X Studio.exe"

        if exe.exists():
            exe.rename(target_exe)

    elif sys.platform == "darwin":
        source = dist / "main.app"
        target = dist / "Display X Studio.app"

        if target.exists():
            shutil.rmtree(target)

        source.rename(target)

    else:
        source = dist / "main.dist"
        target = dist / "Display X Studio"

        if target.exists():
            shutil.rmtree(target)

        source.rename(target)

        exe = target / "main.bin"
        target_exe = target / "Display X Studio"

        if exe.exists():
            exe.rename(target_exe)
            target_exe.chmod(0o755)

    print("Normalized Nuitka output:")
    print(dist)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
