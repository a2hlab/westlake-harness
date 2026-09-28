#!/usr/bin/env bash
# demo_up.sh <SERIAL=61b06572>
# Canonical post-boot bring-up = persist_demo.sh <SERIAL> up (starts host window + on-screen keeper +
# open-broker, in the right order with ensure_host wait). After this, tap any of the 13 home-screen
# icons -> that app renders to first screen. Toutiao = its own red icon (imehost).
HERE="$(cd "$(dirname "$0")" && pwd)"; SERIAL="${1:-61b06572}"
exec bash "$HERE/persist_demo.sh" "$SERIAL" up
