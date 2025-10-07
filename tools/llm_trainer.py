# tools/llm_trainer.py
# Fine-tune local LLM (vLLM Qwen) with data from site agents

import os, json
from pymongo import MongoClient
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, PeftModel
from datasets import Dataset

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=__import__("sys").stderr, flush=True)

# Config
MONGO_URL = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("MONGO_DB","ai_agents_db")
MODEL_NAME = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")  # Smaller model
OUTPUT_DIR = "./models/fine_tuned_qwen"

def prepare_training_data() -> Dataset:
    """
    Load content from site agents and prepare for fine-tuning.
    """
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]

    # Get all site content
    docs = list(db.site_content.find({}, {"url": 1, "content": 1, "domain": 1}))
    log(f"Loaded {len(docs)} documents from agents")

    # Format as instruction-response pairs
    data = []
    for doc in docs:
        content = doc.get("content", "")[:1000]  # limit
        domain = doc.get("domain", "")
        instruction = f"Provide information about {domain} based on the following content:"
        response = f"Based on {domain}: {content}"

        data.append({
            "instruction": instruction,
            "input": content,
            "output": response
        })

    return Dataset.from_list(data)

def fine_tune_llm():
    """
    Fine-tune Qwen with LoRA using agent data.
    """
    log("Starting fine-tuning...")

    # Load model and tokenizer with quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, quantization_config=bnb_config, device_map={"": 0})  # Single GPU
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    # Prepare data
    dataset = prepare_training_data()

    def tokenize_function(examples):
        prompts = [f"Instruction: {inst}\nInput: {inp}\nOutput: {out}" for inst, inp, out in zip(examples["instruction"], examples["input"], examples["output"])]
        return tokenizer(prompts, truncation=True, padding="max_length", max_length=256)
        tokenized["labels"] = tokenized["input_ids"].copy()  # For causal LM loss
        return tokenized

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # Training args
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=1,  # Start with 1 epoch
        per_device_train_batch_size=1,  # Smaller batch
        gradient_accumulation_steps=4,
        save_steps=500,
        logging_steps=10,
        learning_rate=2e-4,
        fp16=True,
        dataloader_pin_memory=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    log(f"Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    fine_tune_llm()
