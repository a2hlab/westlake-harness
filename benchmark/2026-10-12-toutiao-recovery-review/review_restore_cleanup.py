import importlib.util
import inspect
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'evidence/restore-257e-b5904'


def main():
    path = FROZEN / 't0/benchmark/2026-10-12-v1-seal-assembly/toutiao_provider.py'
    spec = importlib.util.spec_from_file_location('frozen_restore_257e', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    main_tree = HERE.parents[2] / 'westlake-harness'
    module.RELEASE = main_tree / 'benchmark/2026-10-12-recovery-executor'
    module.ALIASES = main_tree / 'benchmark/2026-10-12-recovery-exe-alias'
    module.WS = HERE.parents[2]
    original = module.RecordingDevice.shell
    observations = []

    def injected(device, name, script):
        if name == 'remove-empty-owned-storage-directory':
            frame = next(entry.frame for entry in inspect.stack()
                         if entry.function == 'rollback')
            receipt = frame.f_locals['out'] / 'rollback.json'
            observations.append({
                'operation': name,
                'receipt_exists_before_failed_cleanup': receipt.exists(),
                'receipt': json.loads(receipt.read_text()) if receipt.exists() else None,
                'injected_failure': 'rmdir rejects nonempty storage directory',
            })
            raise ValueError('INDEPENDENT nonempty storage directory')
        return original(device, name, script)

    module.RecordingDevice.shell = injected
    case = module.ProviderTests('test_standard_argv_actual_apply_and_rollback')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
    report = {
        'candidate_commit': '257e829b3d5989fad43474fce3e858854cc0e326',
        'device_calls': 0,
        'expected_author_test_failure_observed': len(result.failures) == 1,
        'observations': observations,
        'finding': 'ROLLBACK_RECEIPT_PRECEDES_STORAGE_CLEANUP',
    }
    print(json.dumps(report, indent=2))
    return 0 if (len(result.failures) == 1 and observations
                 and observations[0]['receipt_exists_before_failed_cleanup']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
