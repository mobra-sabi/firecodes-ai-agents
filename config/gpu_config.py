import os

# Configurare pentru toate 11 GPU-urile
ALL_GPUS = "0,1,2,3,4,5,6,7,8,9,10"
TENSOR_PARALLEL_SIZE = 11

# Configurare optimizată pentru Qwen pe 11 GPU-uri
QWEN_CONFIG = {
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    "tensor_parallel_size": TENSOR_PARALLEL_SIZE,
    "gpu_memory_utilization": 0.85,
    "max_model_len": 8192,
    "max_num_seqs": 32
}

def set_all_gpus():
    os.environ["CUDA_VISIBLE_DEVICES"] = ALL_GPUS
    return ALL_GPUS
