#!/usr/bin/env bash
set -euo pipefail
USER="${1:-mobra-sabi}"
REPO="${2:-firecodes-ai-agents}"

git remote add origin "git@github.com:${USER}/${REPO}.git" 2>/dev/null || \
git remote set-url origin "git@github.com:${USER}/${REPO}.git"

git add -A
git commit -m "Sync" || true
git branch -M main
git push -u origin main
git remote -v
