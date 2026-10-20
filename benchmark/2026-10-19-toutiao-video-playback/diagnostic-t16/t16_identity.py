"""Isolated 5cd Guard for T16 (base5 blocker 1) via dependency injection — NOT a global mutation.

R13's archived identity.py binds SERIAL with `from core import ... SERIAL`, and Guard.capture reads that
module-global SERIAL in every device argv (`held <serial>` and `hdc -t <serial> shell`). Rather than
rebinding the shared public `identity` module (a side-effect every importer would see), we load the EXACT
pinned R13 identity source into a UNIQUELY-NAMED private module, bind 5cd only on that private module, and
expose a Guard subclass of its Guard. Because capture reads its defining module's global SERIAL, the private
Guard targets 5cd while the public `identity` module and the archived file stay untouched. Inject it via the
R13 Session's guard_factory. The verified R13 behaviour (bookended on-device boot/UID/exe/module/tracer
checks — the original gate) is reused verbatim; only the serial constant differs, and it is asserted with a
61b/empty serial refused."""
import hashlib, importlib.util, sys
from pathlib import Path
import t16_core

# core.py + identity.py of the pinned reuse base (identical blobs to t16_observer.R13_PINS).
R13_IDENTITY_PINS = {
    'core.py': '422dc30f148aa9730a9847117e50692e8a5b72eda6acef13b5c2d129fdfe21b6',
    'identity.py': '06526af29e9a5df6187154236376761b150572bae94318640d74d80102e70c50',
}
FORBIDDEN_SERIAL = '61b0657200000000000000000324012c'   # 61b — must never reach a 5cd device argv
_PRIVATE_NAME = 't16_r13_identity_5cd'                   # unique private module — never the public 'identity'


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _load_private_identity(r13_dir):
    """Load the pinned R13 identity.py into an isolated private module (NOT sys.modules['identity']), bind
    5cd on that private module, and return it. The archived file and the public `identity` are untouched."""
    d = Path(r13_dir).resolve()
    for n, h in R13_IDENTITY_PINS.items():
        if _sha(d / n) != h:
            raise t16_core.Refuse('R13 identity source drift ' + n + ' (pinned reuse base changed)')
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))   # so the private module's `from core import ...` resolves the pinned core
    mod = sys.modules.get(_PRIVATE_NAME)
    if mod is None:
        spec = importlib.util.spec_from_file_location(_PRIVATE_NAME, str(d / 'identity.py'))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_PRIVATE_NAME] = mod
        spec.loader.exec_module(mod)
    if not t16_core.SERIAL or t16_core.SERIAL == FORBIDDEN_SERIAL:
        raise t16_core.Refuse('refuse to inject a 61b/empty serial')
    mod.SERIAL = t16_core.SERIAL
    if mod.SERIAL != t16_core.SERIAL or mod.SERIAL == FORBIDDEN_SERIAL:
        raise t16_core.Refuse('5cd serial rebind failed on the private identity module')
    return mod


def make_guard(r13_dir):
    """Return a 5cd-targeting Guard class (subclass of the pinned R13 Guard on the private module). Inject
    this as the R13 Session's guard_factory so every device argv carries 5cd, never 61b. Behaviour is the
    reused R13 Guard; only the private-module SERIAL differs."""
    mod = _load_private_identity(r13_dir)

    class Guard(mod.Guard):
        pass

    Guard.__name__ = Guard.__qualname__ = 'T16Guard5cd'
    return Guard
