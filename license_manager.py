from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from PyQt5.QtCore import QEventLoop, QThread, QTimer, pyqtSignal

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
AUTHORIZATION_CACHE_VERSION = 2


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


def permanent_key_matches(mode: str | None, authorized: bool) -> bool:
    """Check whether the server granted permanent authorization."""
    return (
        authorized
        and isinstance(mode, str)
        and mode.strip().lower() == "permanent"
    )


def temporary_key_matches(record: dict | None, key: str | None) -> bool:
    """Check whether a signed server assertion matches a local key."""
    if not isinstance(record, dict) or not isinstance(key, str):
        return False

    key_hash = record.get("key_hash")

    if not isinstance(key_hash, str) or not key_hash:
        return False

    return _key_hash(key) == key_hash


def _get_public_key() -> Ed25519PublicKey:
    """Load the embedded Ed25519 public verification key."""
    key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)

    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Embedded authorization public key is invalid.")

    return key


def verify_signed_authorization(record: dict) -> bool:
    """
    Verify a signed authorization assertion returned by the license Worker.

    Expected structure:

        {
            "version": 1,
            "authorized": true,
            "mode": "temporary",
            "key_hash": "...",
            "issued_at": 1234567890,
            "expires": 1234568190,
            "signature": "base64..."
        }
    """
    if not isinstance(record, dict):
        return False

    signature_b64 = record.get("signature")

    if not isinstance(signature_b64, str) or not signature_b64.strip():
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

        if signed_data.get("version") != 1:
            return False

        issued_at = signed_data.get("issued_at")
        expires = signed_data.get("expires")

        if not isinstance(issued_at, int) or not isinstance(expires, int):
            return False

        now = __import__("time").time()

        if now > expires:
            return False

        if expires <= issued_at:
            return False

        return True

    except Exception:
        return False


def is_authorized(record: dict | None) -> bool:
    """Return whether a signed server assertion currently authorizes the app."""
    if not verify_signed_authorization(record or {}):
        return False

    return bool((record or {}).get("authorized"))

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

class AuthorizationWorker(QThread):
    result_ready = pyqtSignal(object)

    def run(self):
        try:
            self.result_ready.emit(self.fetch())
        except Exception as e:
            self.result_ready.emit(e)

    @staticmethod
    def fetch():
        manager = LicenseManager()
        return manager.fetch_online_authorization()


class LicenseManager:
    """
    Runtime authorization controller.

    The manager:
      1. Reads the signed online authorization record.
      2. Applies the permanent/temporary-key rules.
      3. Prompts for a new key when authorization is required.
      4. Saves a successfully entered key locally.
    """

    # Cloudflare Worker licensing API.
    AUTHORIZATION_URL = "https://displayx-license-api.dxsl.workers.dev"
    STATUS_URL = f"{AUTHORIZATION_URL}/status"
    AUTHORIZE_URL = f"{AUTHORIZATION_URL}/authorize"

    def __init__(self, parent=None):
        self.parent = parent
        self._authorized = False

    def fetch_online_authorization(self) -> dict | None:
        """Fetch the signed server authorization status."""
        try:
            from urllib.request import Request, urlopen

            request = Request(
                self.STATUS_URL,
                headers={
                    "User-Agent": "Display-X-Studio-License/2.0",
                    "Accept": "application/json",
                },
            )

            with urlopen(request, timeout=10) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

            if not isinstance(data, dict):
                return None

            return data

        except Exception:
            return None

    def authorize_with_key(self, entered_key: str) -> bool:
        """Send a user-entered key to the server and verify its signed response."""
        try:
            from urllib.request import Request, urlopen

            normalized = _normalize_key(entered_key)

            if not normalized:
                return False

            body = json.dumps({
                "key": normalized,
            }).encode("utf-8")

            request = Request(
                self.AUTHORIZE_URL,
                data=body,
                method="POST",
                headers={
                    "User-Agent": "Display-X-Studio-License/2.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

            with urlopen(request, timeout=10) as response:
                record = json.loads(
                    response.read().decode("utf-8")
                )

            if not isinstance(record, dict):
                return False

            if not verify_signed_authorization(record):
                return False

            if not bool(record.get("authorized")):
                return False

            if record.get("mode") != "temporary":
                return False

            if not temporary_key_matches(record, normalized):
                return False

            save_local_temp_key(normalized)

            try:
                save_cached_authorization(record)
            except Exception:
                pass

            self._authorized = True
            return True

        except Exception:
            return False

    def authorize_with_record(self, entered_key: str, record: dict) -> bool:
        """Authorize against a signed server assertion."""
        try:
            if not verify_signed_authorization(record):
                return False

            if not bool(record.get("authorized")):
                return False

            if record.get("mode") != "temporary":
                return False

            if not temporary_key_matches(record, entered_key):
                return False

            save_local_temp_key(entered_key)

            try:
                save_cached_authorization(record)
            except Exception:
                pass

            self._authorized = True
            return True

        except Exception:
            return False

    def check_current_authorization(self) -> bool:
        """Check current server authorization, falling back to a valid cache."""
        record = self.fetch_online_authorization()

        if record is not None and is_authorized(record):
            if permanent_key_matches(
                record.get("mode"),
                bool(record.get("authorized")),
            ):
                self._authorized = True
                try:
                    save_cached_authorization(record)
                except Exception:
                    pass
                return True

            local_key = get_local_temp_key()

            if temporary_key_matches(record, local_key):
                self._authorized = True
                try:
                    save_cached_authorization(record)
                except Exception:
                    pass
                return True

            self._authorized = False
            return False

        cached = get_cached_authorization()

        if cached is not None and is_authorized(cached):
            if permanent_key_matches(
                cached.get("mode"),
                bool(cached.get("authorized")),
            ):
                self._authorized = True
                return True

            local_key = get_local_temp_key()

            if temporary_key_matches(cached, local_key):
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

    def _fetch_online_authorization_responsive(self):
        """Fetch online authorization without blocking the Qt GUI."""
        worker = AuthorizationWorker()
        loop = QEventLoop()
        result = [None]
        finished = [False]

        def on_result(value):
            result[0] = value
            finished[0] = True
            loop.quit()

        worker.result_ready.connect(on_result)
        worker.start()

        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(loop.quit)
        timeout_timer.start(11000)

        loop.exec_()

        if not finished[0]:
            worker.quit()
            worker.wait(100)
            return None, False

        worker.quit()
        worker.wait()

        if isinstance(result[0], Exception):
            return None, False

        return result[0], True

    def ensure_authorized(self) -> bool:
        """
        Check live server authorization first.

        The cached signed assertion is used only when the server
        cannot be reached.
        """
        if self._authorized:
            return True

        if self.is_session_bypass_authorized():
            self._authorized = True
            return True

        record, online_available = self._fetch_online_authorization_responsive()

        if online_available:
            if record is not None and is_authorized(record):
                mode = record.get("mode")

                if permanent_key_matches(
                    mode,
                    bool(record.get("authorized")),
                ):
                    try:
                        save_cached_authorization(record)
                    except Exception:
                        pass

                    self._authorized = True
                    return True

                if mode == "temporary":
                    local_key = get_local_temp_key()

                    if temporary_key_matches(record, local_key):
                        try:
                            save_cached_authorization(record)
                        except Exception:
                            pass

                        self._authorized = True
                        return True

            self._authorized = False

        else:
            cached = get_cached_authorization()

            if cached is not None and is_authorized(cached):
                mode = cached.get("mode")

                if permanent_key_matches(
                    mode,
                    bool(cached.get("authorized")),
                ):
                    self._authorized = True
                    return True

                if mode == "temporary":
                    local_key = get_local_temp_key()

                    if temporary_key_matches(cached, local_key):
                        self._authorized = True
                        return True

        # If the server is reachable but /status says a license is required,
        # silently revalidate the saved temporary key before prompting the user.
        saved_key = get_local_temp_key()

        if saved_key:
            if self.authorize_with_key(saved_key):
                return True

        entered_key = self.request_key()

        if not entered_key:
            return False

        return self.authorize_with_key(entered_key)
