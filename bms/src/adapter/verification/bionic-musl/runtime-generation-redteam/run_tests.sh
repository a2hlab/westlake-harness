#!/usr/bin/env bash
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1

python3 "$HERE/tests/test_verify_candidate.py"
echo "RUNTIME_GENERATION_REDTEAM_PASS positive=1 mutants=20 cli=1"
