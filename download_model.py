from huggingface_hub import snapshot_download
import os

# Config
MODEL_ID = "Qwen/Qwen2.5-72B-Instruct-AWQ"
LOCAL_DIR = "/srv/hf/models/Qwen2.5-72B-Instruct-AWQ"

print(f"🚀 Starting download for {MODEL_ID}...")
print(f"📂 Destination: {LOCAL_DIR}")

snapshot_download(
    repo_id=MODEL_ID,
    local_dir=LOCAL_DIR,
    local_dir_use_symlinks=False,
    resume_download=True
)

print("✅ Download complete!")

