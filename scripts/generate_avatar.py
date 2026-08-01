from __future__ import annotations

import argparse
import base64
from pathlib import Path

from openai import OpenAI

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import load_api_key  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="gpt-image-1")
    args = parser.parse_args()

    client = OpenAI(api_key=load_api_key())
    result = client.images.generate(model=args.model, prompt=args.prompt, size="1024x1024")
    image_b64 = result.data[0].b64_json

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(image_b64))
    print(f"saved -> {out_path}")


if __name__ == "__main__":
    main()
