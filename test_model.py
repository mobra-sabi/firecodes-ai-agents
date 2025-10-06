import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_qwen_loading():
    try:
        # Încearcă cu numele oficial al modelului Qwen
        model_name = "Qwen/Qwen2.5-7B"  # sau varianta potrivită
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        print("✅ Qwen 2.5 model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False

if __name__ == "__main__":
    test_qwen_loading()
