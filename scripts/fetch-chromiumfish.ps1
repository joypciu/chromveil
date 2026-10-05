# Download ChromiumFish prebuild into LOCALAPPDATA (Windows) when custom build is not ready.
$ErrorActionPreference = "Stop"
python -m pip install -q "chromiumfish>=0.1" "chromveil[native]" 2>$null
python -m chromiumfish fetch
python -m chromveil.cli doctor
