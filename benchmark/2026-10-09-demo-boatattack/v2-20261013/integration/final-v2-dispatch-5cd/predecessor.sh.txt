#!/bin/bash
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# Explicit v2 staging; all existing v1 routes below remain byte-identical.
for v2_arg in "$@"; do
    case "$v2_arg" in
        --v2-recipe|--v2-recipe=*)
            exec python3 "$SELF_DIR/../../benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-entry/restore_entry.py" "$@"
            ;;
    esac
done
# Explicit directory-complete recipe; legacy and plain realization calls stay unchanged.
for recipe_arg in "$@"; do
    case "$recipe_arg" in
        --directory-recipe|--directory-recipe=*)
            exec python3 "$SELF_DIR/../../benchmark/2026-10-12-exact-realization/r4b-directory-logdir/restore_recipe.py" "$@"
            ;;
    esac
done
# Explicit exact realization; old arguments retain the original restoration entry.
for exact_arg in "$@"; do
    case "$exact_arg" in
        --realization|--realization=*)
            exec python3 "$SELF_DIR/../../benchmark/2026-10-12-exact-realization/r2-timeout/exact_realization.py" "$@"
            ;;
    esac
done
exec python3 "$SELF_DIR/../../benchmark/2026-10-09-demo-baseline/t5/restore.py" "$@"
