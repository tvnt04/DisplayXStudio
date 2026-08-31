from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "main.py"

def main() -> int:
    if not ENTRY.is_file():
        raise SystemExit(f"Application entry point not found: {ENTRY}")

    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)

    dist.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m", "nuitka",
        "--standalone",
        "--follow-imports",
        "--assume-yes-for-downloads",
        f"--output-dir={dist}",
        "--output-filename=Display X Studio",
        "--include-data-file=logo.png=logo.png",
        "--include-data-file=logo_icon.png=logo_icon.png",
        str(ENTRY),
    ]

    if sys.platform == "win32":
        cmd.append("--windows-console-mode=disable")
    elif sys.platform == "darwin":
        cmd += [
            "--macos-create-app-bundle",
            "--macos-app-name=Display X Studio",
            "--macos-app-version=1.4.0",
            "--macos-bundle-identifier=com.tvnt04.displayxstudio",
        ]

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    print(" ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
