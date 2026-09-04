from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PRIVATE_KEY_PATH = (
    Path.home()
    / ".display-x-studio-license"
    / "private_key.pem"
)

OUTPUT_PATH = (
    Path.home()
    / ".display-x-studio-license"
    / "authorization.json"
)


def main() -> None:
    if not PRIVATE_KEY_PATH.is_file():
        raise FileNotFoundError(
            f"Private key not found: {PRIVATE_KEY_PATH}"
        )

    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Invalid Ed25519 private key.")

    authorization_key = input(
        "Enter authorization key to publish: "
    ).strip()

    if not authorization_key:
        raise ValueError("Authorization key cannot be empty.")

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

    record["signature"] = base64.b64encode(signature).decode("ascii")

    OUTPUT_PATH.write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print("Authorization record created:")
    print(OUTPUT_PATH)
    print()
    print("The private key was NOT copied.")
    print("Upload authorization.json to your online authorization location.")


if __name__ == "__main__":
    main()
