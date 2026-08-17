"""Display X Studio update checker.

Checks the latest public GitHub Release and identifies the appropriate
download asset for the current platform.

Installation is intentionally handled separately per platform.
"""

from __future__ import annotations
import os
import tempfile
from pathlib import Path
import json
import platform
import re
from dataclasses import dataclass
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

    @property
    def update_available(self) -> bool:
        return _version_key(self.latest_version) > _version_key(
            self.current_version
        )


def _version_key(version: str) -> tuple[int, ...]:
    """Convert v1.3.0 / 1.3.0 into comparable integer tuples."""
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


def _platform_asset_suffix() -> str:
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Linux":
        if machine in {"x86_64", "amd64"}:
            return "linux-x86_64"
        return f"linux-{machine}"

    if system == "Windows":
        if machine in {"x86_64", "amd64"}:
            return "windows-x86_64"
        return f"windows-{machine}"

    if system == "Darwin":
        if machine in {"arm64", "aarch64"}:
            return "macos-arm64"

        if machine in {"x86_64", "amd64"}:
            return "macos-x86_64"

        return f"macos-{machine}"

    return f"{system.lower()}-{machine}"


def _find_asset(release: dict) -> tuple[str | None, str | None]:
    system = platform.system()
    machine = platform.machine().lower()

    assets = release.get("assets") or []

    if system == "Linux":
        extensions = (".AppImage",)
        machine_names = {"x86_64", "amd64"}
    elif system == "Windows":
        extensions = (".zip", ".exe")
        machine_names = {"x86_64", "amd64"}
    elif system == "Darwin":
        extensions = (".dmg", ".zip")
        machine_names = {
            "x86_64",
            "amd64",
            "arm64",
            "aarch64",
        }
    else:
        return None, None

    for asset in assets:
        name = str(asset.get("name", ""))
        lower_name = name.lower()

        if not any(
            lower_name.endswith(ext.lower())
            for ext in extensions
        ):
            continue

        # Current release naming:
        # Display-X-Studio-1.3.0-x86_64.AppImage
        if machine in {"x86_64", "amd64"}:
            if "x86_64" in lower_name or "amd64" in lower_name:
                return (
                    asset.get("name"),
                    asset.get("browser_download_url"),
                )

        elif machine in {"arm64", "aarch64"}:
            if "arm64" in lower_name or "aarch64" in lower_name:
                return (
                    asset.get("name"),
                    asset.get("browser_download_url"),
                )

    return None, None


def check_for_update(
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> UpdateInfo:
    """Query the latest public GitHub Release."""

    request = Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Display-X-Studio-Updater",
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

    latest_version = str(tag_name).lstrip("vV")

    try:
        _version_key(APP_VERSION)
        _version_key(latest_version)

    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc

    asset_name, asset_url = _find_asset(release)

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_url=release.get("html_url") or "",
        asset_name=asset_name,
        asset_url=asset_url,
    )

def download_update(
    update: UpdateInfo,
    destination: str | Path | None = None,
    timeout: int = 60,
) -> Path:
    """Download the selected update asset to a local file."""

    if not update.asset_url or not update.asset_name:
        raise RuntimeError(
            "No compatible update asset is available."
        )

    if destination is None:
        destination = (
            Path(tempfile.gettempdir())
            / update.asset_name
        )
    else:
        destination = Path(destination)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = Request(
        update.asset_url,
        headers={
            "User-Agent": "Display-X-Studio-Updater",
            "Accept": "application/octet-stream",
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
            with open(temporary, "wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    output.write(chunk)

        os.replace(temporary, destination)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
    ) as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

        raise RuntimeError(
            f"Could not download update: {exc}"
        ) from exc

    return destination

