#!/bin/bash
# Make public copies of raw build logs: <name>.sanitized.txt with $HOME replaced. Raw originals stay
# untouched in the private LOGDIR; their SHA256 is recorded in raw-log-manifest.txt.
# Usage: sanitize_logs.sh <raw LOGDIR> <public dir>
set -euo pipefail
RAW=$1; PUB=$2; mkdir -p "$PUB"
: > "$PUB/raw-log-manifest.txt"
echo "# raw originals (private, persistent): \$HOME${RAW#$HOME}" >> "$PUB/raw-log-manifest.txt"
for f in "$RAW"/*.txt; do
  b=$(basename "$f" .txt)
  echo "$(shasum -a 256 "$f" | cut -d' ' -f1)  $b.txt" >> "$PUB/raw-log-manifest.txt"
  sed "s#$HOME#\$HOME#g" "$f" > "$PUB/$b.sanitized.txt"
done
