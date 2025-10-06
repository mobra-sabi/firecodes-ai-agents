import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import Dataset, load_dataset
import json
import os

# Configurează toate GPU-urile
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7,8,9,10"

class QwenFineTuner:
    def __init__(self):
        self.model_name = "Qwen/Qwen2.5-7B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Configurează tokenizer
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
    def load_training_data(self, file_path):
        """Încarcă datele de antrenament din JSONL"""
        data = []
        print(f"📂 Încărcare date din {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    item = json.loads(line.strip())
                    data.append(item)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Eroare la linia {line_num}: {e}")
                    
        print(f"✅ Încărcate {len(data)} exemple de antrenament")
        return data
        
    def format_training_example(self, example):
        """Formatează exemplul pentru Qwen Instruct"""
        instruction = example['instruction']
        output = example['output']
        
        # Format Qwen Instruct
        formatted = f"<|im_start|>system\nEști un consultant expert în protecția la foc.<|im_end|>\n<|im_start|>user\n{instruction}<|im_end|>\n<|im_start|>assistant\n{output}<|im_end|>"
        
        return formatted
        
    def prepare_dataset(self, data):
        """Pregătește dataset-ul pentru antrenament"""
        print("🔄 Pregătire dataset...")
        
        # Formatează toate exemplele
        formatted_texts = [self.format_training_example(item) for item in data]
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                padding=True,
                max_length=1024,
                return_tensors="pt"
            )
        
        # Creează dataset
        dataset = Dataset.from_dict({"text": formatted_texts})
        tokenized_dataset = dataset.map(
            tokenize_function, 
            batched=True,
            remove_columns=dataset.column_names
        )
        
        print(f"✅ Dataset pregătit cu {len(tokenized_dataset)} exemple")
        return tokenized_dataset
        
    def fine_tune(self, dataset_path, output_dir="./qwen_firestopping_model"):
        """Fine-tuning Qwen pe toate GPU-urile"""
        print("🚀 Începe fine-tuning Qwen...")
        
        # Încarcă modelul distribuit pe toate GPU-urile
        print("📥 Încărcare model Qwen...")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
            attn_implementation="flash_attention_2"  # Pentru performanță
        )
        
        # Încarcă și pregătește datele
        training_data = self.load_training_data(dataset_path)
        train_dataset = self.prepare_dataset(training_data)
        
        # Split pentru validare
        train_size = int(0.9 * len(train_dataset))
        val_size = len(train_dataset) - train_size
        
        train_dataset, val_dataset = torch.utils.data.random_split(
            train_dataset, [train_size, val_size]
        )
        
        # Configurare antrenament optimizată pentru 11 GPU-uri
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=2,  # Batch mic per GPU
            per_device_eval_batch_size=2,
            gradient_accumulation_steps=8,  # Compensează batch-ul mic
            warmup_steps=100,
            learning_rate=1e-5,  # Learning rate conservativ
            weight_decay=0.01,
            fp16=True,
            dataloader_pin_memory=False,
            save_strategy="epoch",
            evaluation_strategy="steps",
            eval_steps=50,
            logging_steps=10,
            save_total_limit=3,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            report_to=None,  # Dezactivează wandb
            ddp_find_unused_parameters=False,
        )
        
        # Data collator pentru language modeling
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal LM
            pad_to_multiple_of=8
        )
        
        # Creează trainer-ul
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
        )
        
        print(f"🔥 Începe antrenamentul pe {torch.cuda.device_count()} GPU-uri...")
        print(f"📊 Antrenament: {len(train_dataset)} exemple")
        print(f"📊 Validare: {len(val_dataset)} exemple")
        
        # Rulează antrenamentul
        trainer.train()
        
        # Salvează modelul final
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)
        
        print(f"🎉 Fine-tuning completat!")
        print(f"💾 Model salvat în: {output_dir}")
        
        return output_dir
