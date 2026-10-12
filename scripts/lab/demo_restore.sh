#!/bin/bash
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# Explicit directory-complete recipe; legacy and plain realization calls stay unchanged.
for recipe_arg in "$@"; do
    case "$recipe_arg" in
        --directory-recipe|--directory-recipe=*)
            exec python3 "$SELF_DIR/../../benchmark/2026-10-12-exact-realization/r4-directory-supplement/restore_recipe.py" "$@"
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
