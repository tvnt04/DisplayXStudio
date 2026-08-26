"""Display X Studio update checker and installation detection."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app_version import APP_VERSION


GITHUB_OWNER = "tvnt04"
GITHUB_REPO = "DisplayXStudio"

RELEASES_API_URL = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str
    asset_name: str | None
    asset_url: str | None
    installation_type: str

    @property
    def update_available(self) -> bool:
        return _version_key(self.latest_version) > _version_key(
            self.current_version
        )


def _version_key(version: str) -> tuple[int, ...]:
    value = str(version).strip().lstrip("vV")

    match = re.match(
        r"^(\d+(?:\.\d+)*)(?:[-+].*)?$",
        value,
    )

    if not match:
        raise ValueError(
            f"Unsupported version format: {version!r}"
        )

    return tuple(
        int(part)
        for part in match.group(1).split(".")
    )


def _running_executable() -> Path | None:
    try:
        if platform.system() == "Linux":
            return Path(
                os.readlink("/proc/self/exe")
            ).resolve()

        return Path(sys.executable).resolve()

    except (OSError, RuntimeError):
        return None


def _is_deb_install(executable: Path | None) -> bool:
    if executable is None:
        return False

    try:
        result = subprocess.run(
            [
                "dpkg-query",
                "-S",
                str(executable),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        return (
            result.returncode == 0
            and "display-x-studio" in result.stdout.lower()
        )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return False


def _is_rpm_install(executable: Path | None) -> bool:
    if executable is None:
        return False

    try:
        result = subprocess.run(
            [
                "rpm",
                "-qf",
                str(executable),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        return (
            result.returncode == 0
            and "display-x-studio" in result.stdout.lower()
        )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return False


def detect_installation_type() -> str:
    """Detect how the running application was installed."""

    system = platform.system()
    executable = _running_executable()

    if system == "Linux":
        appimage = os.environ.get("APPIMAGE")

        if appimage:
            appimage_path = Path(appimage).resolve()

            if (
                appimage_path.is_file()
                and appimage_path.suffix.lower() == ".appimage"
            ):
                return "linux-appimage"

        if _is_deb_install(executable):
            return "linux-deb"

        if _is_rpm_install(executable):
            return "linux-rpm"

        return "unsupported"

    if system == "Windows":
        if executable:
            install_dir = executable.parent

            if any(
                install_dir.glob("unins*.exe")
            ):
                return "windows-installer"

            if "program files" in str(
                install_dir
            ).lower():
                return "windows-installer"

        return "windows-portable"

    if system == "Darwin":
        if executable:
            for parent in executable.parents:
                if parent.suffix.lower() == ".app":
                    return "macos-dmg"

        return "unsupported"

    return "unsupported"


def _asset_matches(
    name: str,
    installation_type: str,
) -> bool:
    lower = name.lower()

    if installation_type == "linux-appimage":
        return (
            lower.endswith(".appimage")
            and (
                "linux-x86_64" in lower
                or "linux-amd64" in lower
            )
        )

    if installation_type == "linux-deb":
        return (
            lower.endswith(".deb")
            and (
                "amd64" in lower
                or "x86_64" in lower
            )
        )

    if installation_type == "linux-rpm":
        return (
            lower.endswith(".rpm")
            and (
                "x86_64" in lower
                or "amd64" in lower
            )
        )

    if installation_type == "windows-installer":
        return (
            lower.endswith(".exe")
            and "setup" in lower
        )

    if installation_type == "windows-portable":
        return (
            lower.endswith(".zip")
            and "windows-x86_64" in lower
        )

    if installation_type == "macos-dmg":
        return (
            lower.endswith(".dmg")
            and (
                "macos-arm64" in lower
                or "macos-x86_64" in lower
            )
        )

    return False


def _find_asset(
    release: dict,
    installation_type: str,
) -> tuple[str | None, str | None]:

    for asset in release.get("assets") or []:
        name = str(
            asset.get("name", "")
        )

        if _asset_matches(
            name,
            installation_type,
        ):
            return (
                asset.get("name"),
                asset.get(
                    "browser_download_url"
                ),
            )

    return None, None


def check_for_update(
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> UpdateInfo:
    """Query the latest public GitHub Release."""

    request = Request(
        RELEASES_API_URL,
        headers={
            "Accept":
                "application/vnd.github+json",
            "User-Agent":
                "Display-X-Studio-Updater",
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            release = json.load(response)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
    ) as exc:
        raise RuntimeError(
            f"Could not check for updates: {exc}"
        ) from exc

    except (
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            "GitHub returned invalid release metadata"
        ) from exc

    tag_name = release.get("tag_name")

    if not tag_name:
        raise RuntimeError(
            "Latest GitHub Release has no tag_name"
        )

    latest_version = str(
        tag_name
    ).lstrip("vV")

    _version_key(APP_VERSION)
    _version_key(latest_version)

    installation_type = (
        detect_installation_type()
    )

    asset_name, asset_url = _find_asset(
        release,
        installation_type,
    )

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_url=release.get(
            "html_url"
        ) or "",
        asset_name=asset_name,
        asset_url=asset_url,
        installation_type=installation_type,
    )


def download_update(
    update: UpdateInfo,
    destination: str | Path | None = None,
    timeout: int = 60,
) -> Path:
    """Download the selected update asset."""

    if (
        not update.asset_url
        or not update.asset_name
    ):
        raise RuntimeError(
            "No compatible update asset is available."
        )

    if destination is None:
        destination = (
            Path(tempfile.gettempdir())
            / update.asset_name
        )
    else:
        destination = Path(
            destination
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = Request(
        update.asset_url,
        headers={
            "User-Agent":
                "Display-X-Studio-Updater",
            "Accept":
                "application/octet-stream",
        },
    )

    temporary = destination.with_suffix(
        destination.suffix + ".download"
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            with open(
                temporary,
                "wb",
            ) as output:

                while True:
                    chunk = response.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    output.write(chunk)

        os.replace(
            temporary,
            destination,
        )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
    ) as exc:

        try:
            temporary.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise RuntimeError(
            f"Could not download update: {exc}"
        ) from exc

    return destination