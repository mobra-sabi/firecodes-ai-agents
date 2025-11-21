#!/bin/bash
# Build Frontend for Production

cd "$(dirname "$0")/../frontend"
echo "🏗️  Building Frontend for Production..."
npm run build
echo "✅ Build complete! Files in: frontend/dist/"

