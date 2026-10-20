"""T16 observer = R13's proven Session device glue, REUSED unchanged except:
  (1) admission validated by t16_core.t16_validate (5cd, fresh profile, player pivot),
  (2) prepare_addresses reads the player-GOT offsets from the admission (player-SHA bound),
  (3) result schema relabelled.
R13 core/observer/identity are imported from the pinned diagnostic-r13 dir (SHA-verified); this file
never copies or hot-modifies the archived files. The only adaptation to the board identity is t16_identity
loading the pinned R13 identity into an ISOLATED private module bound to 5cd and injected as the Session
guard_factory (blocker 1); the public `identity` module and the archived files stay untouched. lldb is
imported only inside entry()."""
import hashlib, json, signal, sys, time
from pathlib import Path
import t16_core
import t16_identity

make_guard = t16_identity.make_guard   # expose the 5cd guard_factory for the outer + base5's re-verification

R13_PINS = {
    'core.py': '422dc30f148aa9730a9847117e50692e8a5b72eda6acef13b5c2d129fdfe21b6',
    'identity.py': '06526af29e9a5df6187154236376761b150572bae94318640d74d80102e70c50',
    'observer.py': 'c3a28ec8740c002f99a7c3cab413a58845f9001fd44f99496b45ffde0511f15f',
}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_r13(r13_dir):
    """SHA-verify the pinned R13 source, put it on sys.path, import its modules. Reuse, never copy."""
    d = Path(r13_dir).resolve()
    for n, h in R13_PINS.items():
        if _sha(d / n) != h:
            raise t16_core.Refuse('R13 source drift ' + n + ' (pinned reuse base changed)')
    sys.path.insert(0, str(d))
    import core as r13core
    import observer as r13observer
    return r13core, r13observer


def make_session_class(r13observer):
    class T16Session(r13observer.Session):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.result['schema'] = 't16-result-v1'

        def prepare_addresses(self):
            # Identical to R13 except the (slot, expected_elf, pc) triples come from the admission,
            # so a re-derived player (b427614d) supplies its own GOT offsets. Shim lock pc stays 0x5e48.
            from core import biases, need as r13need
            p = self.a['modules']['player']
            bs = biases(self.rows, p)
            r13need(len(bs) == 1, 'ambiguous player instance')
            pb = bs[0]
            for x in self.a['addresses']:
                role, slot, expected, pc = x['role'], x['slot'], x['expected_elf'], x['pc']
                actual = int.from_bytes(self.read(pb + slot, 8), 'little')
                winner = self.module(actual)
                r13need(winner['role'] == role and int(winner['elf_address'], 16) == expected,
                        'actual player GOT drift ' + role)
                self.selected[role] = int(winner['bias'], 16) + pc
                self.emit({'kind': 'actual_binding', 'slot': hex(pb + slot), 'provider': winner})
    return T16Session


def entry(admission, out, port, r13_dir):
    """Run inside the pinned SDK15 host python (outer execute). Reuses R13 Session.run + its os._exit fail-safe."""
    r13core, r13observer = load_r13(r13_dir)
    import lldb
    a = json.loads(Path(admission).read_text())
    t16_core.t16_validate(a)
    T16Session = make_session_class(r13observer)
    s = T16Session(lldb, lldb.debugger, a, out, guard_factory=t16_identity.make_guard(r13_dir))

    def cancel(signum, frame):
        s.cancel = True
        s.deadline = min(s.deadline, time.monotonic())
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    result = s.run(port)
    if not result['cleanup']['verified']:
        import os
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(2)
    return result
