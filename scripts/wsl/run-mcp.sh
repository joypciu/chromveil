#!/usr/bin/env bash
set -euo pipefail
source "${HOME}/.chromveil/venv/bin/activate"
[[ -f "${HOME}/.chromveil/env" ]] && source "${HOME}/.chromveil/env"
exec python -m chromveil.mcp_server
