# tools/llm_key_loader.py
import os, pathlib

# Ordinea de căutare:
#   1) OPENAI_API_KEY (dacă e deja în ENV)
#   2) fișier din OPENAI_KEY_FILE (dacă e setat)
#   3) ~/.config/ai_agents/openai.key  (global user)
#   4) <repo>/.secrets/openai.key      (local în repo)
CANDIDATES = [
    os.getenv("OPENAI_KEY_FILE"),
    str(pathlib.Path("~/.config/ai_agents/openai.key").expanduser()),
    str(pathlib.Path(__file__).resolve().parents[1] / ".secrets" / "openai.key"),
]

def ensure_openai_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if key:
        return key
    for p in CANDIDATES:
        if not p:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                key = f.read().strip()
            if key:
                os.environ["OPENAI_API_KEY"] = key  # disponibil pentru restul codului
                return key
        except FileNotFoundError:
            continue
    return ""
