#!/bin/bash

# Qwen2.5-7B cu TP=2 pe porturile 9301-9304
nohup vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 9301 --tensor-parallel-size 2 --max-model-len 4096 --gpu-memory-utilization 0.85 --dtype float16 > ~/ai_agents/logs/vllm_9301.log 2>&1 &
nohup vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 9302 --tensor-parallel-size 2 --max-model-len 4096 --gpu-memory-utilization 0.85 --dtype float16 > ~/ai_agents/logs/vllm_9302.log 2>&1 &
nohup vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 9303 --tensor-parallel-size 2 --max-model-len 4096 --gpu-memory-utilization 0.85 --dtype float16 > ~/ai_agents/logs/vllm_9303.log 2>&1 &
nohup vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 9304 --tensor-parallel-size 2 --max-model-len 4096 --gpu-memory-utilization 0.85 --dtype float16 > ~/ai_agents/logs/vllm_9304.log 2>&1 &

# Qwen2.5-14B cu TP=7 pe portul 9310 (folosind 7 GPU-uri)
nohup vllm serve Qwen/Qwen2.5-14B-Instruct --host 0.0.0.0 --port 9310 --tensor-parallel-size 7 --max-model-len 8192 --gpu-memory-utilization 0.90 --dtype float16 > ~/ai_agents/logs/vllm_9310.log 2>&1 &

echo "✅ Cluster vLLM pornit cu 5 instanțe"
echo "📊 Ports: 9301-9304 (Qwen2.5-7B), 9310 (Qwen2.5-14B)"
