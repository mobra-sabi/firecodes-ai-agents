#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20
cd /srv/hf/ai_agents/frontend/dist
exec serve -s . -l 4000

