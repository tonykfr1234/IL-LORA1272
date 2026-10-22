#!/usr/bin/env python3
"""Create private Docker Compose settings without printing or replacing secrets."""

from pathlib import Path
import os
import secrets
import sys


def main() -> int:
    destination = Path(__file__).resolve().parents[1] / ".env"
    settings = "\n".join(
        [
            "# Local private settings. Never commit this file.",
            "DB_PASSWORD=" + secrets.token_hex(32),
            "DB_ROOT_PASSWORD=" + secrets.token_hex(32),
            "IOT_API_KEY=" + secrets.token_hex(32),
            "APP_PORT=8080",
            "",
        ]
    )
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(".env already exists; kept the existing credentials.", file=sys.stderr)
        return 1
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        output.write(settings)
    print("Created private .env. Start with: docker compose up --build -d --wait")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
