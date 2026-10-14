#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == --help ]]; then
  printf '%s\n' 'LAB_HOME=<persistent home> bash execute-hw248.sh <new attempt directory>'
  printf '%s\n' 'Uses only locked FZ002 archives; restores private dependencies and executes the provider compiler/link commands. No VM/device access.'
  exit 0
fi
: "${LAB_HOME:?explicit persistent home required}"
[[ $# == 1 && "$1" == /* && ! -e "$1" ]] || { printf '%s\n' 'REFUSE: attempt must be a new absolute directory' >&2; exit 2; }
ATTEMPT="$1"
mkdir -p "$ATTEMPT"
DEPS="$LAB_HOME/westlake-oh6.1-b9-v3-74d1d6d4-source"
run_step() {
  local name="$1"
  shift
  set +e
  "$@" >"$ATTEMPT/$name.stdout" 2>"$ATTEMPT/$name.stderr"
  local status=$?
  set -e
  printf '%s\n' "$status" >"$ATTEMPT/$name.rc"
  cat "$ATTEMPT/$name.stdout"
  cat "$ATTEMPT/$name.stderr" >&2
  return "$status"
}
run_step generation-lock python3 "$HERE/acquire.py" --id FZ002_GENERATION --archive "$DEPS/build-inputs.tar.gz" --receipt-dir "$ATTEMPT/generation-lock"
run_step external-lock python3 "$HERE/acquire.py" --id FZ002_PLATFORM_LINK --archive "$DEPS/external-link-inputs.tar.gz" --receipt-dir "$ATTEMPT/external-lock"
run_step restore python3 "$HERE/restore_provider_inputs.py" --inputs "$DEPS/build-inputs.tar.gz" --external "$DEPS/external-link-inputs.tar.gz" --out "$ATTEMPT/generation"
run_step provider python3 "$HERE/build_provider.py" --generation "$ATTEMPT/generation" --out "$ATTEMPT/provider" --run
