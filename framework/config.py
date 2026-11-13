"""Configuration from environment variables.

Precedence: shell / CI variables, then the project's `.env`, then the defaults below.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Absolute path, so it works from any working directory; shell / CI values win.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _get(name: str, default: str) -> str:
    # An empty value (e.g. an unset CI secret) means "use the default".
    return os.environ.get(name) or default


BASE_URL: str = _get("BASE_URL", "https://qae-assignment-tau.vercel.app").rstrip("/")
USER_ID: str = _get("USER_ID", "candidate-hUyKPqFY2gaP")
HEADLESS: bool = _get("HEADLESS", "true").lower() in ("1", "true", "yes")

# Explicit-wait timeout (seconds) for UI steps.
DEFAULT_TIMEOUT: int = 10


def app_url() -> str:
    """App URL authenticated as the configured user."""
    return f"{BASE_URL}/?user-id={USER_ID}"
