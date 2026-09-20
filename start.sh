#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -n "$MINERAL_ATLAS_PYTHON" ]; then
  exec "$MINERAL_ATLAS_PYTHON" atlas_cli.py serve --out ./atlas-runs --open
elif [ -f .atlas-python ] && [ -x "$(cat .atlas-python)" ]; then
  exec "$(cat .atlas-python)" atlas_cli.py serve --out ./atlas-runs --open
elif [ -x .venv/bin/python ]; then
  exec .venv/bin/python atlas_cli.py serve --out ./atlas-runs --open
else
  exec python3 atlas_cli.py serve --out ./atlas-runs --open
fi
