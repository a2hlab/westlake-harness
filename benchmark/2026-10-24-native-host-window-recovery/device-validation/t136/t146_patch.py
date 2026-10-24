"""T146 test-only patches: make T136 tests runnable on a fresh clone.

Patches the module under test IN TESTS ONLY (originals untouched):
- m.INPUT            -> temp dir with synthetic rollback.so/candidate.so
- m.BASELINE/CANDIDATE-> synthetic SHAs (digest of the synthetic bytes)
- m.IDLE_SOURCE(_SHA)-> public fixture copy + recomputed SHA
Also exposes fixture paths. No device, no real .so, no .private runs.
"""
import hashlib
import importlib
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / 'fixtures' / 'identity'

SYNTH_BASELINE = b'T146-SYNTHETIC-BASELINE' + b'\x00' * 37
SYNTH_CANDIDATE = b'T146-SYNTHETIC-CANDIDATE' + b'\x01' * 41
SYNTH_BASELINE_SHA = hashlib.sha256(SYNTH_BASELINE).hexdigest()
SYNTH_CANDIDATE_SHA = hashlib.sha256(SYNTH_CANDIDATE).hexdigest()

RUN_031657 = 'execute-20261025-031657-eafd14'
RUN_033355 = 'execute-20261025-033355-1e6bc7'
RUN_032931 = 'execute-20261025-032931-2688cd'
RUN_034802 = 'execute-20261025-034802-6bb129'


def fixture(*rel) -> Path:
    return FIX.joinpath(*rel)


def synth_input_dir() -> tempfile.TemporaryDirectory:
    """Temp INPUT dir containing rollback.so/candidate.so synthetic bytes."""
    d = tempfile.TemporaryDirectory(prefix='t146-input-')
    p = Path(d.name)
    (p / 'rollback.so').write_bytes(SYNTH_BASELINE)
    (p / 'candidate.so').write_bytes(SYNTH_CANDIDATE)
    return d


_KEEP_ALIVE = []


def normalized_idle_source(m):
    """Write a temp IDLE_SOURCE copy whose object.sha256 matches the synthetic BASELINE;
    point m.IDLE_SOURCE(_SHA) at it so admit() re-parse sees consistent synthetic sha."""
    import hashlib as _h, json as _j
    data = _j.loads(m.IDLE_SOURCE.read_text())
    data['object']['sha256'] = m.BASELINE
    tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, prefix='t146-idle-')
    _j.dump(data, tmp); tmp.close()
    p = Path(tmp.name)
    m.IDLE_SOURCE = p
    m.IDLE_SOURCE_SHA = _h.sha256(p.read_bytes()).hexdigest()
    return p


def patch_module(m):
    """Apply test-only attribute patches to an imported execute_vN module."""
    import types
    holder = types.SimpleNamespace(_input_dir=None)

    class _InputPath(str):
        """Path-like stand-in resolving synthetic files; str subclass keeps q()/joins working."""

        def __truediv__(self, other):
            return Path(str(self)) / other

        def __fspath__(self):
            return str(self)

    d = synth_input_dir()
    _KEEP_ALIVE.append(d)
    m.INPUT = _InputPath(d.name)
    m.BASELINE = SYNTH_BASELINE_SHA
    m.CANDIDATE = SYNTH_CANDIDATE_SHA
    # Version detection MUST use m.__file__ basename: tests import via spec loaders whose
    # __name__ (e.g. 't136_entry') does not carry the version.
    import os as _os
    base = _os.path.basename(str(getattr(m, '__file__', '')))
    idle_rel = {
        'execute.py': ('execute-20261025-024115-2e76dc', 'baseline-s30-binding.json'),
        'execute_v3.py': ('execute-20261025-024115-2e76dc', 'baseline-s30-binding.json'),
        'execute_v4.py': ('execute-20261025-024115-2e76dc', 'baseline-s30-binding.json'),
        'execute_v5.py': ('execute-20261025-025346-5209f4', 'baseline-s30-binding.json'),
        'execute_v6.py': ('execute-20261025-030926-e8956c', 'baseline-s30-binding.json'),
        'execute_v7.py': ('execute-20261025-032931-2688cd', 'baseline-early-17-binding.json'),
    }.get(base, (RUN_034802, 'restored-idle-binding.json'))
    idle = fixture(*idle_rel)
    if hasattr(m, 'IDLE_SOURCE'):
        m.IDLE_SOURCE = idle
        m.IDLE_SOURCE_SHA = hashlib.sha256(idle.read_bytes()).hexdigest()
        normalized_idle_source(m)
    return holder
