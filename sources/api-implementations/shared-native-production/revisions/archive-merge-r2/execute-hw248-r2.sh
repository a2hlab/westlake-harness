#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$HERE/../.." && pwd)"
: "${LAB_HOME:?explicit persistent home required}"
[[ $# == 1 && "$1" == /* && ! -e "$1" ]] || exit 2
ATTEMPT="$1"
mkdir -p "$ATTEMPT"
DEPS="$LAB_HOME/westlake-oh6.1-b9-v3-74d1d6d4-source"
run_step() {
  local name="$1"
  shift
  set +e
  "$@" >"$ATTEMPT/$name.stdout" 2>"$ATTEMPT/$name.stderr"
  local result=$?
  set -e
  printf '%s\n' "$result" >"$ATTEMPT/$name.rc"
  cat "$ATTEMPT/$name.stdout"
  cat "$ATTEMPT/$name.stderr" >&2
  return "$result"
}
run_step restore python3 "$HERE/restore_provider_inputs_r2.py" --inputs "$DEPS/build-inputs.tar.gz" --external "$DEPS/external-link-inputs.tar.gz" --out "$ATTEMPT/generation"
run_step provider python3 "$SOURCE/build_provider.py" --generation "$ATTEMPT/generation" --out "$ATTEMPT/provider" --run
