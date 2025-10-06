import os
from pathlib import Path

# Locațiile unde vom căuta cheile (în ordinea priorității)
OPENAI_KEY_PATHS = [
    Path(os.getenv("AI_AGENTS_OPENAI_KEY_FILE", "")),          # override explicit
    Path.cwd() / ".secrets" / "openai.key",                     # repo local
    Path.home() / ".config" / "ai_agents" / "openai.key",       # global user
]
BRAVE_KEY_PATHS = [
    Path(os.getenv("AI_AGENTS_BRAVE_KEY_FILE", "")),
    Path.cwd() / ".secrets" / "brave.key",
    Path.home() / ".config" / "ai_agents" / "brave.key",
]

def _read_first_existing(paths):
    for p in paths:
        if not p:
            continue
        try:
            if p.is_file():
                v = p.read_text(encoding="utf-8").strip()
                if v:
                    return v
        except Exception:
            pass
    return ""

def _ensure_file(path: Path, placeholder=""):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(placeholder, encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
    except Exception:
        pass

def get_openai_key() -> str:
    # 1) ENV are prioritate
    k = (os.getenv("OPENAI_API_KEY") or "").strip()
    if k:
        return k

    # 2) Fișiere
    k = _read_first_existing(OPENAI_KEY_PATHS).strip()
    if k:
        return k

    # 3) Nu există → creăm placeholder în repo și în home și explicăm
    repo = Path.cwd() / ".secrets" / "openai.key"
    home = Path.home() / ".config" / "ai_agents" / "openai.key"
    _ensure_file(repo, "")
    _ensure_file(home, "")
    msg = (
        "OPENAI_API_KEY indisponibil.\n"
        f"→ Pune cheia ta în: {repo}\n"
        f"   (sau) {home}\n"
        "   conținutul fișierului = cheia pe un singur rând, fără newline la final.\n"
        "Poți rula și: tools/set_openai_key.sh"
    )
    raise SystemExit(msg)

def get_brave_key() -> str:
    # 1) ENV
    k = (os.getenv("BRAVE_API_KEY") or "").strip()
    if k:
        return k

    # 2) Fișiere
    k = _read_first_existing(BRAVE_KEY_PATHS).strip()
    if k:
        return k

    # 3) Placeholder + mesaj
    repo = Path.cwd() / ".secrets" / "brave.key"
    home = Path.home() / ".config" / "ai_agents" / "brave.key"
    _ensure_file(repo, "")
    _ensure_file(home, "")
    msg = (
        "BRAVE_API_KEY indisponibil.\n"
        f"→ Pune cheia Brave în: {repo}\n"
        f"   (sau) {home}\n"
        "   conținutul fișierului = cheia pe un singur rând."
    )
    raise SystemExit(msg)
