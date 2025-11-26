#!/bin/bash

# Config
MODEL_PATH="/srv/hf/models/Qwen2.5-72B-Instruct-AWQ"
PORT=8000
# Folosim 8 GPU-uri pentru viteză maximă și lăsăm 2 libere (8,9) pentru Embeddings/Qdrant
TENSOR_PARALLEL=8 
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

GPU_MEMORY_UTILIZATION=0.90 

echo "🚀 Starting Local LLM (Qwen 72B) on port $PORT..."
echo "   GPUs: $TENSOR_PARALLEL (IDs: 0-7)"

# Activam env
source /home/mobra/aienv/bin/activate

# Pornim serverul vLLM
# --max-model-len 16384: Context size generos
# --quantization awq: Specific pentru modelul descărcat
python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_PATH \
    --port $PORT \
    --tensor-parallel-size $TENSOR_PARALLEL \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --max-model-len 16384 \
    --trust-remote-code \
    --quantization awq \
    --dtype auto \
    --enforce-eager \
    --served-model-name "local-qwen"
