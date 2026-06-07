#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -x "$DIR/.venv/bin/python" ]; then
  python3 -m venv .venv
fi

"$DIR/.venv/bin/pip" install -q -r requirements.txt
chmod +x "$DIR/gui" "$DIR/ai-council" "$DIR/串供"
exec "$DIR/gui"
