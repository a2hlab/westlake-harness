#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${FN01_HDC_INVOCATION_MARKER:-}" ]]; then
  printf 'invoked\n' >>"$FN01_HDC_INVOCATION_MARKER"
fi
echo "FORBIDDEN_HDC_TEST_DOUBLE_INVOKED" >&2
exit 99
