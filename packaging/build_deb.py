from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
DEB_ROOT = ROOT / "packaging" / "deb"
DIST_DIR = ROOT / "dist" / "Display X Studio"


def get_version() -> str:
    version_file = ROOT / "app_version.py"
    text = version_file.read_text(encoding="utf-8")

    match = re.search(
        r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']',
        text,
        re.MULTILINE,
    )

    if not match:
        raise RuntimeError("Could not find APP_VERSION in app_version.py")

    return match.group(1)


def main() -> int:
    version = get_version()

    if not DIST_DIR.is_dir():
        raise RuntimeError(
            f"PyInstaller output not found: {DIST_DIR}"
        )

    opt_dir = DEB_ROOT / "opt" / "display-x-studio"

    if opt_dir.exists():
        shutil.rmtree(opt_dir)

    opt_dir.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copytree(
        DIST_DIR,
        opt_dir,
    )

    control = DEB_ROOT / "DEBIAN" / "control"
    text = control.read_text(encoding="utf-8")

    text = re.sub(
        r"^Version: .*$",
        f"Version: {version}",
        text,
        flags=re.MULTILINE,
    )

    control.write_text(
        text,
        encoding="utf-8",
    )

    output = ROOT / (
        f"Display-X-Studio-{version}-amd64.deb"
    )

    if output.exists():
        output.unlink()

    subprocess.run(
        [
            "dpkg-deb",
            "--build",
            str(DEB_ROOT),
            str(output),
        ],
        check=True,
    )

    print(f"Created: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
