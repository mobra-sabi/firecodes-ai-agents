#!/bin/bash
##################################################
# 🚀 PORNIRE CLUSTER vLLM PARALEL
# Folosește GPU-urile 6-10 pentru 4 instanțe Qwen
##################################################

LOG_DIR="/srv/hf/ai_agents/logs"
mkdir -p "$LOG_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  🚀 PORNIRE CLUSTER vLLM - 4 INSTANȚE PARALELE                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Stop instanțe existente pe porturile 9302-9304
for port in 9302 9303 9304; do
    PID=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "⚠️  Opresc instanță existentă pe port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null
        sleep 2
    fi
done

echo ""
echo "🎮 PORNIRE INSTANȚE vLLM:"
echo ""

# Instanță 1: GPU 6-7 → Port 9302
echo "   [1/4] Port 9302 (GPU 6-7)..."
CUDA_VISIBLE_DEVICES=6,7 nohup vllm serve Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 9302 \
    --tensor-parallel-size 2 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --dtype float16 \
    --max-num-seqs 16 \
    > "$LOG_DIR/vllm_9302.log" 2>&1 &
sleep 3

# Instanță 2: GPU 8 → Port 9303
echo "   [2/4] Port 9303 (GPU 8)..."
CUDA_VISIBLE_DEVICES=8 nohup vllm serve Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 9303 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --dtype float16 \
    --max-num-seqs 8 \
    > "$LOG_DIR/vllm_9303.log" 2>&1 &
sleep 3

# Instanță 3: GPU 9 → Port 9304
echo "   [3/4] Port 9304 (GPU 9)..."
CUDA_VISIBLE_DEVICES=9 nohup vllm serve Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 9304 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --dtype float16 \
    --max-num-seqs 8 \
    > "$LOG_DIR/vllm_9304.log" 2>&1 &
sleep 3

# Instanță 4: GPU 10 → Port 9305
echo "   [4/4] Port 9305 (GPU 10)..."
CUDA_VISIBLE_DEVICES=10 nohup vllm serve Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 --port 9305 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --dtype float16 \
    --max-num-seqs 8 \
    > "$LOG_DIR/vllm_9305.log" 2>&1 &

echo ""
echo "⏳ Aștept 60s ca toate instanțele să pornească..."
sleep 60

echo ""
echo "✅ VERIFICARE INSTANȚE:"
echo ""
for port in 9302 9303 9304 9305; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "   ✅ Port $port: ONLINE"
    else
        echo "   ❌ Port $port: OFFLINE (verifică log: $LOG_DIR/vllm_$port.log)"
    fi
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅ CLUSTER vLLM PORNIT!                                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
