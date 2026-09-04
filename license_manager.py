from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app_paths import get_app_data_path


# ---------------------------------------------------------------------------
# Display X Studio authorization
# ---------------------------------------------------------------------------

# This is the permanent authorization built into the application.
#
# Change this only when intentionally creating a new application build.
PERMANENT_KEY = "TVNT"


# Public key corresponding to the developer's private signing key.
#
# The private key NEVER belongs in the application.
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEApWKVqh9zvD/2m1qJ1XvQ2zwufpUKvXnQIDB5us0fRj0=
-----END PUBLIC KEY-----
"""


TEMP_KEY_FILENAME = "license.json"
CACHED_AUTHORIZATION_FILENAME = "authorization_cache.json"


def _normalize_key(value: str) -> str:
    """Normalize an authorization key before comparison."""
    return "".join(str(value).strip().upper().split())


def _key_hash(value: str) -> str:
    """Return a SHA-256 fingerprint for an authorization key."""
    return hashlib.sha256(
        _normalize_key(value).encode("utf-8")
    ).hexdigest()


def get_local_license_path() -> Path:
    """Return the local authorization file path."""
    return Path(get_app_data_path(TEMP_KEY_FILENAME))


def get_local_temp_key() -> str | None:
    """Read the locally stored temporary authorization key."""
    path = get_local_license_path()

    try:
        if not path.is_file():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        key = data.get("temporary_key")

        if not isinstance(key, str) or not key.strip():
            return None

        return key.strip()

    except Exception:
        return None


def save_local_temp_key(key: str) -> None:
    """Save the temporary authorization key locally."""
    normalized = _normalize_key(key)

    if not normalized:
        raise ValueError("Authorization key cannot be empty.")

    path = get_local_license_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "temporary_key": normalized,
    }

    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def clear_local_temp_key() -> None:
    """Remove the locally stored temporary authorization key."""
    path = get_local_license_path()

    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def permanent_key_matches(online_key: str | None) -> bool:
    """Check whether the online key matches the permanent key."""
    if not online_key:
        return False

    return _key_hash(online_key) == _key_hash(PERMANENT_KEY)


def temporary_key_matches(online_key: str | None) -> bool:
    """Check whether the online key matches the local temporary key."""
    if not online_key:
        return False

    local_key = get_local_temp_key()

    if not local_key:
        return False

    return _key_hash(online_key) == _key_hash(local_key)


def _get_public_key() -> Ed25519PublicKey:
    """Load the embedded Ed25519 public verification key."""
    key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)

    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Embedded authorization public key is invalid.")

    return key


def verify_signed_authorization(record: dict) -> bool:
    """
    Verify that the online authorization record was signed
    using the developer's private key.

    Expected structure:

        {
            "version": 1,
            "authorization_key": "ABC123",
            "signature": "base64..."
        }
    """
    if not isinstance(record, dict):
        return False

    authorization_key = record.get("authorization_key")
    signature_b64 = record.get("signature")

    if not isinstance(authorization_key, str):
        return False

    if not authorization_key.strip():
        return False

    if not isinstance(signature_b64, str):
        return False

    if not signature_b64.strip():
        return False

    try:
        signature = base64.b64decode(
            signature_b64.encode("ascii"),
            validate=True,
        )

        signed_data = {
            key: value
            for key, value in record.items()
            if key != "signature"
        }

        message = json.dumps(
            signed_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        _get_public_key().verify(signature, message)

        return True

    except Exception:
        return False


def is_authorized(record: dict | None) -> bool:
    """
    Apply the Display X Studio three-key authorization logic.

    1. Online authorization must have a valid developer signature.
    2. If Online == Permanent -> authorized.
    3. Otherwise, if Online == Temporary -> authorized.
    4. Otherwise -> unauthorized.
    """
    if not verify_signed_authorization(record or {}):
        return False

    online_key = record.get("authorization_key")

    if not isinstance(online_key, str):
        return False

    # Master authorization:
    # Online == Permanent
    if permanent_key_matches(online_key):
        return True

    # Normal customer authorization:
    # Online == Temporary
    if temporary_key_matches(online_key):
        return True

    return False

# ---------------------------------------------------------------------------
# Cached online authorization
# ---------------------------------------------------------------------------

def get_cached_authorization_path() -> Path:
    """Return the local cache path for the last known-good online record."""
    return Path(get_app_data_path(CACHED_AUTHORIZATION_FILENAME))


def get_cached_authorization() -> dict | None:
    """Read the last known-good signed authorization record."""
    path = get_cached_authorization_path()

    try:
        if not path.is_file():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            return None

        if not verify_signed_authorization(data):
            return None

        return data

    except Exception:
        return None


def save_cached_authorization(record: dict) -> None:
    """Save a verified online authorization record for offline use."""
    if not verify_signed_authorization(record):
        raise ValueError("Cannot cache an unsigned or invalid authorization record.")

    path = get_cached_authorization_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Runtime license manager
# ---------------------------------------------------------------------------

class LicenseManager:
    """
    Runtime authorization controller.

    The manager:
      1. Reads the signed online authorization record.
      2. Applies the permanent/temporary-key rules.
      3. Prompts for a new key when authorization is required.
      4. Saves a successfully entered key locally.
    """

    # Set this to the actual online authorization.json URL later.
    AUTHORIZATION_URL = "https://raw.githubusercontent.com/tvnt04/DXSL/main/authorization.json"

    def __init__(self, parent=None):
        self.parent = parent
        self._authorized = False

    def fetch_online_authorization(self) -> dict | None:
        """
        Fetch the current signed authorization record.

        The URL is intentionally empty until the developer chooses
        the online authorization location.
        """
        if not self.AUTHORIZATION_URL:
            return None

        try:
            from urllib.request import Request, urlopen

            request = Request(
                self.AUTHORIZATION_URL,
                headers={
                    "User-Agent": "Display-X-Studio-License/1.0",
                    "Accept": "application/json",
                },
            )

            with urlopen(request, timeout=10) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

            return data if isinstance(data, dict) else None

        except Exception:
            return None

    def check_current_authorization(self) -> bool:
        """
        Check authorization using the online record first.

        If the network is temporarily unavailable, use the last
        known-good signed authorization record.
        """
        record = self.fetch_online_authorization()

        if record is not None:
            if is_authorized(record):
                try:
                    save_cached_authorization(record)
                except Exception:
                    pass

                self._authorized = True
                return True

            self._authorized = False
            return False

        # Network unavailable: use the last verified authorization record.
        cached = get_cached_authorization()

        if cached is not None and is_authorized(cached):
            self._authorized = True
            return True

        self._authorized = False
        return False

    def request_key(self) -> str | None:
        """Ask the user for an authorization key."""
        try:
            from PyQt5.QtWidgets import QInputDialog

            key, accepted = QInputDialog.getText(
                self.parent,
                "Authorization Required",
                "Enter authorization key:",
            )

            if not accepted:
                return None

            key = key.strip()

            if not key:
                return None

            return key

        except Exception:
            return None

    def begin_session_bypass(self, required_steps: int) -> bool:
        """
        Begin a developer-only session bypass sequence.

        The bypass exists only in memory and disappears when the
        application process exits.
        """
        try:
            required_steps = int(required_steps)
        except (TypeError, ValueError):
            return False

        if required_steps < 1 or required_steps > 20:
            return False

        self._bypass_required_steps = required_steps
        self._bypass_completed_steps = 0
        self._session_bypass_authorized = False
        return True

    def verify_bypass_password(self, password: str) -> bool:
        return password.strip().upper() == "TVNT"

    def complete_session_bypass_step(self, password: str) -> tuple[bool, str]:
        """
        Complete one developer bypass step.

        Returns:
            (success, status_message)
        """
        required = getattr(self, "_bypass_required_steps", 0)
        completed = getattr(self, "_bypass_completed_steps", 0)

        if required < 1:
            return False, "No bypass sequence is active."

        if self._session_bypass_authorized:
            return True, "Developer session bypass already active."

        if not self.verify_bypass_password(password):
            return False, "Bypass authentication failed."

        completed += 1
        self._bypass_completed_steps = completed

        if completed >= required:
            self._session_bypass_authorized = True
            return True, "Developer session bypass activated."

        remaining = required - completed
        return True, f"Bypass step accepted. {remaining} step(s) remaining."

    def is_session_bypass_authorized(self) -> bool:
        """Return whether the current process has developer bypass access."""
        return bool(
            getattr(self, "_session_bypass_authorized", False)
        )

    def ensure_authorized(self) -> bool:
        """
        Ensure the application is authorized to load data.

        Fast paths use existing in-memory authorization or the last
        verified local cache. If no cached authorization exists, show
        the authorization dialog immediately and perform the online
        verification only after the user submits a key.
        """

        if self._authorized:
            return True

        if self.is_session_bypass_authorized():
            self._authorized = True
            return True

        # Fast path: last known-good signed authorization.
        cached = get_cached_authorization()
        if cached is not None and is_authorized(cached):
            self._authorized = True
            return True

        # No cached authorization.
        # Ask for the key FIRST so the UI never waits for GitHub
        # before displaying the authorization dialog.
        entered_key = self.request_key()

        if not entered_key:
            return False

        # Only perform the network request after the user has entered
        # a key.
        record = self.fetch_online_authorization()

        if record is None:
            return False

        if not verify_signed_authorization(record):
            return False

        online_key = record.get("authorization_key")

        if not isinstance(online_key, str):
            return False

        if _normalize_key(entered_key) != _normalize_key(online_key):
            return False

        save_local_temp_key(entered_key)

        try:
            save_cached_authorization(record)
        except Exception:
            pass

        self._authorized = True
        return True
