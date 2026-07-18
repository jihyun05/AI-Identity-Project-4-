from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_api_key(path: str | Path = ROOT / "apikey.txt") -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()
