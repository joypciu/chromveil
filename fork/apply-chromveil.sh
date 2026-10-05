#!/usr/bin/env bash
# Apply ChromVeil patches on top of an already-patched ChromiumFish src/ tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FISH_ROOT="${CHROMIUMFISH_ROOT:-/mnt/e/chromiumfish}"
SRC="${FISH_ROOT}/src"
PATCH_DIR="${ROOT}/fork/patches"

if [[ ! -d "$SRC" ]]; then
  echo "error: $SRC not found. Build ChromiumFish first (see scripts/wsl/build-chromiumfish.sh)." >&2
  exit 1
fi

for patch in "$PATCH_DIR"/*.patch; do
  [[ -f "$patch" ]] || continue
  echo "Applying $(basename "$patch") ..."
  git -C "$SRC" apply --3way "$patch" || git -C "$SRC" apply --reject "$patch"
done

echo "ChromVeil patches applied. Rebuild: autoninja -C out/Release chrome"
