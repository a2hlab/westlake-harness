#!/usr/bin/env python3
"""Create a synthetic, non-deployable fixture for controller dry-run evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.experiments.d600.fn01_provenance.test_final_generation_controller import (
    make_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise SystemExit(f"refuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    spec = make_fixture(output_dir)
    value = json.loads(spec.read_text(encoding="utf-8"))
    value["fixture_kind"] = "SYNTHETIC_CONTRACT_ONLY"
    spec.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"FIXTURE_KIND=SYNTHETIC_CONTRACT_ONLY")
    print("ELIGIBLE_FOR_DEPLOY=false")
    print(f"SPEC={spec.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
