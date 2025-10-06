#!/usr/bin/env bash
set -euo pipefail

TS="$(date +'%Y%m%d_%H%M%S')"
OUTDIR="exports"
ARCHIVE="firecodes_project_${TS}.tar.gz"

mkdir -p "$OUTDIR"

# încercăm să generăm un requirements freeze (opțional)
if command -v python >/dev/null 2>&1; then
  mkdir -p "$OUTDIR/meta"
  python - <<'PY' || true
import os, subprocess, sys, pathlib
p = pathlib.Path("exports/meta/requirements-freeze.txt")
try:
    out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    p.write_text(out)
    print("[i] requirements-freeze salvat în", p)
except Exception as e:
    print("[!] nu am putut genera requirements-freeze:", e)
PY
fi

# mic README despre secrete
mkdir -p .secrets
cat > .secrets/README_DO_NOT_COMMIT.txt <<'TXT'
Nu pune cheile în arhivă.
Setează-le local rulând:
  bash tools/configure_openai_key.sh
și pune tokenul Brave în:
  printf '%s' 'BSA_...token...' > .secrets/brave.key && chmod 600 .secrets/brave.key
TXT

tar -czf "${OUTDIR}/${ARCHIVE}" \
  --exclude-vcs \
  --exclude='./aienv' \
  --exclude='./.venv' \
  --exclude='**/__pycache__' \
  --exclude='./node_modules' \
  --exclude='./.cache' \
  --exclude='./.pytest_cache' \
  --exclude='./playwright' \
  --exclude='./.env' \
  --exclude='./.secrets/*.key' \
  .

echo "[i] snapshot creat: ${OUTDIR}/${ARCHIVE}"
tar -tzf "${OUTDIR}/${ARCHIVE}" | head -n 25
