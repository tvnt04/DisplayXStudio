from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from license_manager import (
    is_authorized,
    save_local_temp_key,
    clear_local_temp_key,
)


PRIVATE_KEY_PATH = (
    Path.home()
    / ".display-x-studio-license"
    / "private_key.pem"
)


def sign_authorization(authorization_key: str) -> dict:
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Invalid Ed25519 private key.")

    record = {
        "version": 1,
        "authorization_key": authorization_key,
    }

    message = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = private_key.sign(message)

    record["signature"] = base64.b64encode(
        signature
    ).decode("ascii")

    return record


def test_case(
    name: str,
    online_key: str,
    expected: bool,
) -> None:
    record = sign_authorization(online_key)

    result = is_authorized(record)

    status = "PASS" if result == expected else "FAIL"

    print(
        f"{status}: {name} "
        f"(expected={expected}, actual={result})"
    )

    if result != expected:
        raise AssertionError(name)


print("=== Display X Studio Three-Key Tests ===")
print()

# Customer currently has this temporary key.
save_local_temp_key("ABC123")

# ---------------------------------------------------------
# TEST 1
# ---------------------------------------------------------
test_case(
    "Online matches temporary",
    "ABC123",
    True,
)

# ---------------------------------------------------------
# TEST 2
# ---------------------------------------------------------
test_case(
    "Online matches permanent",
    "TVNT",
    True,
)

# ---------------------------------------------------------
# TEST 3
# ---------------------------------------------------------
test_case(
    "Online matches neither",
    "ABC444",
    False,
)

# ---------------------------------------------------------
# TEST 4
# ---------------------------------------------------------
# Sign ABC123 correctly, then change the value to TVNT.
# The signature must fail.
#
tampered_record = sign_authorization("ABC123")
tampered_record["authorization_key"] = "TVNT"

result = is_authorized(tampered_record)

if result:
    raise AssertionError(
        "Tampered authorization was incorrectly accepted."
    )

print("PASS: Tampered signed authorization rejected")

# Clean up the customer's test temporary key.
clear_local_temp_key()

print()
print("ALL LICENSE TESTS PASSED")
