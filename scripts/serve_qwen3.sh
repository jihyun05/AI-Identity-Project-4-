#!/bin/bash
# Launch a Qwen3 vLLM OpenAI-compatible API server on ad005.
# Usage: ./serve_qwen3.sh [1.7b|4b|8b] [gpu_id] [port]
#
# served-model-name is kept as e.g. "Qwen3-8B" to match model_name in
# config/models.yaml, since model_client.py passes model_name straight
# through as the API "model" field.

set -euo pipefail

SIZE="${1:-4b}"
GPU_ID="${2:-0}"
PORT="${3:-8000}"

case "$SIZE" in
  1.7b) MODEL_DIR="$HOME/models/Qwen3-1.7B"; SERVED_NAME="Qwen3-1.7B" ;;
  4b)   MODEL_DIR="$HOME/models/Qwen3-4B";   SERVED_NAME="Qwen3-4B" ;;
  8b)   MODEL_DIR="$HOME/models/Qwen3-8B";   SERVED_NAME="Qwen3-8B" ;;
  *) echo "Unknown size: $SIZE (use 1.7b, 4b, or 8b)"; exit 1 ;;
esac

ENV_BIN="$HOME/miniforge3/envs/qwen3-vllm/bin"
LOG_DIR="$HOME/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${SERVED_NAME}.log"

# VLLM_USE_FLASHINFER_SAMPLER=0: FlashInfer's JIT-compiled sampler fails to
# build on this box (pip nvcc 13.2 vs bundled CCCL headers mismatch), so we
# fall back to vLLM's default sampler instead.
nohup env CUDA_VISIBLE_DEVICES="$GPU_ID" VLLM_USE_FLASHINFER_SAMPLER=0 PATH="$ENV_BIN:$PATH" \
  "$ENV_BIN/vllm" serve "$MODEL_DIR" \
  --served-model-name "$SERVED_NAME" \
  --port "$PORT" \
  --gpu-memory-utilization 0.85 \
  > "$LOG_FILE" 2>&1 &

echo "Launched $SERVED_NAME on GPU $GPU_ID, port $PORT (pid $!)"
echo "Log: $LOG_FILE"
