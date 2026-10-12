"""Explicit collector adapter for frozen realization or R3 activation selfcheck."""
import argparse
from pathlib import Path
import binary_safe_collector as binary


R3_SHA = "2537f4422f544b2831388a95968336e933cd00ecd706951deb849cb3b1740b6c"


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--checker", choices=("realization", "activation"), required=True)
    args, remaining = parser.parse_known_args(argv)
    if args.checker == "realization":
        checker = binary.install(binary.original)
    else:
        checker = binary.load_pinned(binary.FROZEN / "r3-activation-selfcheck/selfcheck.py", "r5_activation_selfcheck", R3_SHA)
        select = checker.select_frozen
        def selected(proof_path):
            select(proof_path)
            binary.install(checker.original_check)
        checker.select_frozen = selected
        binary.install(checker.original_check)
    return checker.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
