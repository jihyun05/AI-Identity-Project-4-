"""Qwen3-VL-4B-Instruct를 순정 transformers로 로드해서 OpenAI 호환
/v1/chat/completions 엔드포인트로 서빙한다 (vLLM 대신 — ad002 GPU 드라이버가
너무 오래돼서 Qwen3-VL을 지원하는 vLLM 빌드가 요구하는 CUDA 버전을 못 맞춤).

사용법:
    python scripts/serve_qwen3vl_transformers.py --port 8000 --gpu 0

우리 harness(src/model_client.py)는 openai 파이썬 SDK로 이 엔드포인트를 호출하므로,
openai ChatCompletion 응답 스키마를 최대한 맞춰서 반환한다.
"""

from __future__ import annotations

import argparse
import threading
import time
import uuid

import torch
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

MODEL_DIR = "/data/jkchoi/models/Qwen3-VL-4B-Instruct"
SERVED_NAME = "Qwen3-VL-4B-Instruct"

app = FastAPI()
_lock = threading.Lock()  # model.generate()를 한 번에 하나씩만 (KV 캐시/컨텍스트 충돌 방지)
_model = None
_processor = None


def _to_qwen_content(content) -> list[dict]:
    """OpenAI 메시지 content(str 또는 [{type:text/image_url}, ...])를
    Qwen processor가 기대하는 형식([{type:text/image}, ...])으로 변환."""
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    parts = []
    for part in content:
        if part.get("type") == "text":
            parts.append({"type": "text", "text": part["text"]})
        elif part.get("type") == "image_url":
            parts.append({"type": "image", "image": part["image_url"]["url"]})
    return parts


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [{"id": SERVED_NAME, "object": "model", "owned_by": "local"}],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = [
        {"role": m["role"], "content": _to_qwen_content(m["content"])}
        for m in body["messages"]
    ]
    max_new_tokens = body.get("max_tokens", 512)

    with _lock:
        inputs = _processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(_model.device)

        out = _model.generate(**inputs, max_new_tokens=max_new_tokens)
        response_text = _processor.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )
        prompt_tokens = inputs["input_ids"].shape[1]
        completion_tokens = out.shape[1] - prompt_tokens

    return JSONResponse(
        {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", SERVED_NAME),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop",
                    "logprobs": None,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
    )


def main():
    global _model, _processor
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()

    device = f"cuda:{args.gpu}"
    print(f"모델 로딩 중... ({MODEL_DIR}, {device})")
    _model = Qwen3VLForConditionalGeneration.from_pretrained(
        MODEL_DIR, torch_dtype=torch.bfloat16, device_map=device
    )
    _processor = AutoProcessor.from_pretrained(MODEL_DIR)
    print("로딩 완료. 서버 시작.")

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
