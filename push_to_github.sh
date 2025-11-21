#!/bin/bash
# 🚀 Script rapid pentru push pe GitHub

set -e

echo "🔍 Verifică status Git..."
git status --short | head -20

echo ""
echo "📦 Adaugă modificările..."
git add .

echo ""
echo "📝 Commit modificările..."
read -p "Mesaj commit (sau Enter pentru mesaj default): " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="Update: Optimizări GPU + ScraperAPI + fix-uri"
fi

git commit -m "$commit_msg"

echo ""
echo "🚀 Push pe GitHub..."
git push origin main

echo ""
echo "✅ Gata! Modificările sunt pe GitHub."
echo ""
echo "💻 Pe laptop, rulează:"
echo "   git pull origin main"

