#!/bin/bash
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# Explicit exact realization; old arguments retain the original restoration entry.
for exact_arg in "$@"; do
    case "$exact_arg" in
        --realization|--realization=*)
            exec python3 "$SELF_DIR/../../benchmark/2026-10-12-exact-realization/exact_realization.py" "$@"
            ;;
    esac
done
exec python3 "$SELF_DIR/../../benchmark/2026-10-09-demo-baseline/t5/restore.py" "$@"
