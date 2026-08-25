from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent.parent
RPM_ROOT = ROOT / "packaging" / "rpm"
DIST_DIR = ROOT / "dist" / "Display X Studio"
SPEC_FILE = RPM_ROOT / "display-x-studio.spec"


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

    if not DIST_DIR.is_dir():
        raise RuntimeError(
            f"PyInstaller output not found: {DIST_DIR}"
        )

    spec_text = SPEC_FILE.read_text(encoding="utf-8")

    spec_text = re.sub(
        r"^Version:\s*.*$",
        f"Version:        {version}",
        spec_text,
        flags=re.MULTILINE,
    )

    spec_text = re.sub(
        r"^\* .* - .*?-1$",
        f"* Display X Studio Team - {version}-1",
        spec_text,
        flags=re.MULTILINE,
    )

    source_dir = RPM_ROOT / "sources"
    if source_dir.exists():
        shutil.rmtree(source_dir)

    source_dir.mkdir(parents=True)

    shutil.copytree(
        DIST_DIR,
        source_dir / "Display-X-Studio",
    )

    shutil.copy2(
        ROOT / "logo_icon.png",
        source_dir / "display-x-studio.png",
    )

    topdir = RPM_ROOT / "rpmbuild"

    if topdir.exists():
        shutil.rmtree(topdir)

    for name in (
        "BUILD",
        "BUILDROOT",
        "RPMS",
        "SOURCES",
        "SPECS",
        "SRPMS",
    ):
        (topdir / name).mkdir(parents=True)

    generated_spec = topdir / "SPECS" / SPEC_FILE.name
    generated_spec.write_text(
        spec_text,
        encoding="utf-8",
    )

    shutil.copytree(
        source_dir / "Display-X-Studio",
        topdir / "SOURCES" / "Display-X-Studio",
    )

    shutil.copy2(
        source_dir / "display-x-studio.png",
        topdir / "SOURCES" / "display-x-studio.png",
    )

    subprocess.run(
        [
            "rpmbuild",
            "--define",
            f"_topdir {topdir}",
            "-bb",
            str(generated_spec),
        ],
        check=True,
    )

    rpms = list(
        (topdir / "RPMS").rglob("*.rpm")
    )

    if not rpms:
        raise RuntimeError("rpmbuild produced no RPM package")

    output = ROOT / (
        f"Display-X-Studio-{version}-x86_64.rpm"
    )

    if output.exists():
        output.unlink()

    shutil.copy2(
        rpms[0],
        output,
    )

    print(f"Created: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
