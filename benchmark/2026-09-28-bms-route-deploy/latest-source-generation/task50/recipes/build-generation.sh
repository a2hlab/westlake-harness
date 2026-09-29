#!/usr/bin/env bash
set -euo pipefail
ROOT=${B6_REPO_ROOT:?}
# First apply r155-namespace.patch to the task47 real-work staging tree.
# The retained-providers SHA guard and source-ledger regeneration remain enabled.
exec bash "$ROOT/bms/src/.work/b6-real-work/build-retained-generation.sh"
