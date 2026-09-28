#!/bin/bash
# stop_by_pattern.sh <regex>: stop processes whose command line matches, never this script itself.
for p in $(pgrep -f -- "$1"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill "$p" 2>/dev/null && echo "stopped $p"; done
