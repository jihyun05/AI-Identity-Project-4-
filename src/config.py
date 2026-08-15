from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def image_data_uri(rel_path: str | Path) -> str:
    path = ROOT / rel_path
    mime, _ = mimetypes.guess_type(path)
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime or 'image/png'};base64,{b64}"


def load_api_key(path: str | Path = ROOT / "apikey.txt") -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key.strip()

    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    raise FileNotFoundError(
        f"OpenAI API key not found. Set the OPENAI_API_KEY environment variable or create {path}."
    )


def load_reminder(path: str | Path = ROOT / "config" / "reminder.yaml") -> str:
    return load_yaml(path)["reminder"]
