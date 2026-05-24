#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

python3 -m pip install pyinstaller

pyinstaller \
  --noconfirm \
  --clean \
  --name EvilHotKeys \
  --windowed \
  --collect-all PIL \
  --add-data "assets:assets" \
  --add-data "games:games" \
  --add-data "libs:libs" \
  evilhotkeys.py

echo "Built executable at: $SCRIPT_DIR/dist/EvilHotKeys/"
