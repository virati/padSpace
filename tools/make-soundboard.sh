#!/usr/bin/env bash
# Regenerate the soundboard TTS samples referenced by config/bindings.conf.
# Only needed if assets/ is lost — install.sh normally copies assets/ directly.
set -euo pipefail
OUT="$HOME/.local/share/padspace"
mkdir -p "$OUT"
espeak-ng -v en-us+m3 -s 145 -p 55 -a 180 -w "$OUT/science-bitch.wav" "science, bitch!"
echo "wrote $OUT/science-bitch.wav"
