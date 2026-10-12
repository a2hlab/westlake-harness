#!/usr/bin/env python3
"""Pin a completed placement's existing receipts; never invent or execute them."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r3_activation_checker', HERE / 'selfcheck.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)


def build(args):
    need = s.need
    need(not args.out.exists() and args.out.parent.is_dir(), 'fresh output in existing directory required')
    parent = s.read(args.execution_receipt)
    need(type(parent.get('executor_rc')) is int and parent['executor_rc'] == 0, 'parent executor_rc must be 0; incomplete/failed execution is not evidence')
    refs = [args.transaction_dir / ('placed-%03d.json' % n) for n in range(487)]
    need(all(path.is_file() for path in refs), 'all 487 original placed receipts are required')
    binding = {'schema': 'exact-activation-selfcheck-binding/v1', 'checker_sha256': s.digest(HERE / 'selfcheck.py'),
               'synthetic': False, 'realization': s.pinned(args.realization),
               'origin_realization': s.pinned(args.origin_realization),
               'prepared_manifest': s.pinned(args.prepared_manifest), 'admission': s.pinned(args.admission),
               'restore_adapter': s.pinned(args.restore_adapter), 'execution_receipt': s.pinned(args.execution_receipt),
               'transaction': s.pinned(args.transaction_dir / 'transaction.json'),
               'placed': s.pinned(args.transaction_dir / 'placed.json'),
               'member_receipts': [s.pinned(path) for path in refs],
               'appendix': s.pinned(args.appendix) if args.appendix else None,
               'execution_cwd': s.portable(args.execution_cwd)}
    # Write only after full admission succeeds, using a temporary local pin file.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='r3-binding-preview-') as directory:
        temporary = Path(directory) / 'binding.json'
        temporary.write_text(json.dumps(binding, indent=2) + '\n')
        s.admit(temporary, s.digest(temporary), offline=True)
    with args.out.open('x') as stream:
        json.dump(binding, stream, indent=2); stream.write('\n')
    return binding


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('realization', 'origin-realization', 'prepared-manifest', 'admission', 'restore-adapter',
                 'execution-receipt', 'transaction-dir', 'execution-cwd', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--appendix', type=Path)
    args = p.parse_args()
    try:
        build(args)
        print('BOUND_EXISTING_RECORDS_ONLY sha256=' + s.digest(args.out)); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('REJECT ' + str(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
