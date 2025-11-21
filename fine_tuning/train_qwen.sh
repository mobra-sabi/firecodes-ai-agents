#!/bin/bash
# 🎯 Fine-Tuning Script pentru Qwen 2.5-72B Local
# Folosește vLLM + LoRA pentru fine-tuning eficient

set -e

# Configurare
MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
BASE_MODEL_PATH="/srv/hf/models/Qwen2.5-72B-Instruct"
DATASET_PATH="/srv/hf/ai_agents/datasets/training_data.jsonl"
OUTPUT_DIR="/srv/hf/ai_agents/fine_tuning/output"
LOG_DIR="/srv/hf/ai_agents/logs"
NUM_GPUS=11
BATCH_SIZE=4
LEARNING_RATE=2e-5
NUM_EPOCHS=3

# Culori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "══════════════════════════════════════════════════════════════"
echo "  🎯 QWEN 2.5-72B FINE-TUNING"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Verifică dataset
if [ ! -f "$DATASET_PATH" ]; then
    echo -e "${RED}❌ Dataset not found: $DATASET_PATH${NC}"
    echo "   Run: python3 /srv/hf/ai_agents/fine_tuning/build_jsonl.py"
    exit 1
fi

DATASET_SIZE=$(wc -l < "$DATASET_PATH")
if [ "$DATASET_SIZE" -lt 100 ]; then
    echo -e "${YELLOW}⚠️  Dataset too small: $DATASET_SIZE lines (minimum: 100)${NC}"
    echo "   Skipping fine-tuning. Need more data."
    exit 0
fi

echo -e "${GREEN}✅ Dataset found: $DATASET_SIZE examples${NC}"
echo ""

# Creează directoare
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# Verifică GPU-uri
echo "🔍 Checking GPUs..."
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader | head -$NUM_GPUS

echo ""
echo "🚀 Starting fine-tuning..."
echo "   • Model: $MODEL_NAME"
echo "   • Dataset: $DATASET_SIZE examples"
echo "   • GPUs: $NUM_GPUS"
echo "   • Batch size: $BATCH_SIZE"
echo "   • Learning rate: $LEARNING_RATE"
echo "   • Epochs: $NUM_EPOCHS"
echo ""

# Fine-tuning cu vLLM + LoRA
# Notă: Ajustează comanda în funcție de setup-ul tău (Axolotl, Unsloth, etc.)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/fine_tune_${TIMESTAMP}.log"

echo "📝 Log file: $LOG_FILE"
echo ""

# Exemplu cu Axolotl (dacă e instalat)
if command -v axolotl &> /dev/null; then
    echo "Using Axolotl for fine-tuning..."
    axolotl train /srv/hf/ai_agents/fine_tuning/axolotl_config.yaml \
        --output_dir "$OUTPUT_DIR" \
        --dataset "$DATASET_PATH" \
        2>&1 | tee "$LOG_FILE"
else
    # Fallback: Python script pentru fine-tuning
    echo "Using Python fine-tuning script..."
    python3 << EOF
import os
import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_dataset

print("Loading model and tokenizer...")
model = AutoModelForCausalLM.from_pretrained(
    "$BASE_MODEL_PATH",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("$BASE_MODEL_PATH")

print("Loading dataset...")
dataset = load_dataset("json", data_files="$DATASET_PATH", split="train")

def tokenize_function(examples):
    # Tokenize messages
    messages = examples["messages"]
    text = tokenizer.apply_chat_template(messages, tokenize=False)
    return tokenizer(text, truncation=True, max_length=4096)

tokenized_dataset = dataset.map(tokenize_function, batched=True)

print("Starting training...")
training_args = TrainingArguments(
    output_dir="$OUTPUT_DIR",
    num_train_epochs=$NUM_EPOCHS,
    per_device_train_batch_size=$BATCH_SIZE,
    learning_rate=$LEARNING_RATE,
    logging_dir="$LOG_DIR",
    save_strategy="epoch",
    bf16=True,
    gradient_accumulation_steps=4,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
)

trainer.train()
trainer.save_model()

print("✅ Fine-tuning completed!")
EOF
    2>&1 | tee "$LOG_FILE"
fi

echo ""
echo -e "${GREEN}✅ Fine-tuning completed!${NC}"
echo "   • Output: $OUTPUT_DIR"
echo "   • Log: $LOG_FILE"
echo ""

# Verifică output
if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A $OUTPUT_DIR)" ]; then
    echo "📊 Model files:"
    ls -lh "$OUTPUT_DIR" | head -10
else
    echo -e "${YELLOW}⚠️  No model files found in output directory${NC}"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"


