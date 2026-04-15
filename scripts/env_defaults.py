from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / ".env"


def read_dotenv_value(env_file: Path, key: str) -> Optional[str]:
    if not env_file.exists():
        return None
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        current_key, value = line.split("=", 1)
        if current_key.strip() != key:
            continue
        value = value.strip().strip('"').strip("'")
        return value or None
    return None


def env_or_dotenv(key: str, default: Optional[str] = None, *, env_file: Path = DEFAULT_ENV_FILE) -> Optional[str]:
    value = os.environ.get(key)
    if value:
        return value
    dotenv_value = read_dotenv_value(env_file, key)
    if dotenv_value:
        return dotenv_value
    return default
