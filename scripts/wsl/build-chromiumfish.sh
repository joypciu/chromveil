#!/usr/bin/env bash
# Full ChromiumFish compile (hours, ~100GB). Run inside WSL only.
set -euo pipefail

FISH="${CHROMIUMFISH_ROOT:-/mnt/e/chromiumfish}"
cd "$FISH"

if [[ ! -d src ]]; then
  echo "Follow https://chromium.googlesource.com/chromium/src/+/main/docs/linux_build_instructions.md"
  echo "Checkout into $FISH/src then re-run."
  exit 1
fi

bash apply.sh
bash /mnt/e/chromveil/fork/apply-chromveil.sh

cd src
gn gen out/Release --args='is_component_build=false is_debug=false symbol_level=0'
autoninja -C out/Release chrome

echo "Set CHROMVEIL_CHROME=$FISH/src/out/Release/chrome"
