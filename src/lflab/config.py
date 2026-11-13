"""Settings come from environment variables (or a .env file).

Every setting is required. If one is missing, the CLI stops with a clear message
instead of guessing a value.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return value


def check_langfuse_settings() -> None:
    """The Langfuse SDK reads these by itself; we only check they exist."""
    for name in ["LANGFUSE_BASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]:
        require(name)
