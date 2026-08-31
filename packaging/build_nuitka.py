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
        cmd.append("--windows-console-mode=disable")

    elif sys.platform == "darwin":
        cmd += [
            "--macos-create-app-bundle",
            f"--macos-app-version={version}",
            "--macos-bundle-identifier=com.tvnt04.displayxstudio",
        ]

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    print("Building with Nuitka:")
    print(" ".join(cmd))

    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
