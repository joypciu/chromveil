#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip curl ca-certificates \
  libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2t64 || \
  sudo apt-get install -y -qq libasound2

VENV="${HOME}/.chromveil/venv"
mkdir -p "${HOME}/.chromveil"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install -U pip wheel

# Editable ChromVeil + ChromiumFish SDK from your Windows drive
pip install -e "/mnt/e/chromveil[native]"
pip install -e "/mnt/e/chromiumfish/packages/python-sdk[agent,mcp]"

playwright install chromium
playwright install-deps chromium 2>/dev/null || true

if chromiumfish fetch; then
  echo "ChromiumFish binary cached."
else
  echo "chromiumfish fetch failed — use a local out/Release/chrome after build."
fi

grep -q CHROMVEIL_PERSONA "${HOME}/.chromveil/env" 2>/dev/null || cat >>"${HOME}/.chromveil/env" <<'EOF'
export CHROMVEIL_PERSONA="joy-1"
export CHROMVEIL_NATIVE=1
export OPENAI_API_BASE="http://127.0.0.1:11434/v1"
export OPENAI_API_KEY="ollama"
export OPENAI_API_MODEL="llama3.2"
EOF

echo "Wrote ${HOME}/.chromveil/env — source it before chromveil mcp."
