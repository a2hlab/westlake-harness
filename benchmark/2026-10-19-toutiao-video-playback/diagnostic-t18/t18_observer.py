"""T18 observer = the T16 observer, specialized to ONE new bridge SHA (single AudioTrack-getter object).

T18 re-links from the original 52-object baseline at exact d4fa and replaces a single audio object, so the
deployed bridge SHA changes. The verified T16 admission gate pins `MODULE_PINS['bridge']` to the old d4fa and
will (correctly) refuse the new bridge. This derivation specializes ONLY that one pin — it is NOT an
arbitrary-pin interface: the new bridge SHA is a hardcoded constant, and every other module pin / address
triple / serial / tool SHA / Guard is kept byte-identical to the SHA-pinned T16 and asserted so. The T16
files are never modified; no HDC here.

Mechanism (same isolation idea as t16_identity): load the SHA-pinned `t16_core` into a UNIQUELY-NAMED private
module, swap only its `MODULE_PINS['bridge']`, assert nothing else moved, and use that private module's
`t16_validate` as the T18 admission gate. The reused R13 Session + injected 5cd Guard are unchanged; the
Guard's on-device module-SHA check then verifies the deployed bridge == the new pin."""
import hashlib, importlib.util, json, signal, sys, time
from pathlib import Path

# Strict source derivation: T18 derives from these EXACT T16 blobs (landed/base5-verified).
T16_SOURCE_PINS = {
    't16_core.py': '5c6cc445706c1a2d74c5d5f429b0bd80da5e6881da77a3dc179933852a359268',
    't16_observer.py': '0f03839acfa94ac5957611bc14a5440cfd65830ec5ba3031a6b76bda429b4631',
    't16_identity.py': '9c34b7e48e626cab5f328457c7275a902f7aecc76e22ff9fa24e710f37d0bcac',  # observer imports it
}
# The ONE new bridge SHA (T18 production-01 candidate.so). base5 ABI review in progress; deploy on notify.
NEW_BRIDGE_SHA = 'dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9'
OLD_BRIDGE_SHA = 'd4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'   # d4fa baseline (T16 pin)
_PRIV = 't18_core_dca530eb'   # unique private module — never the public t16_core


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _verify_source(t16_dir):
    d = Path(t16_dir).resolve()
    for n, h in T16_SOURCE_PINS.items():
        if _sha(d / n) != h:
            raise RuntimeError('T16 source drift ' + n + ' (T18 derives from the pinned T16 only)')
    return d


def load_t18_core(t16_dir):
    """SHA-verify t16_core.py, load it as a private module, swap ONLY MODULE_PINS['bridge'] to the new SHA,
    assert every other pin is byte-identical to the public t16_core, and return the private module whose
    t16_validate is the T18 admission gate. No arbitrary pin is accepted."""
    d = _verify_source(t16_dir)
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    import t16_core as pub
    mod = sys.modules.get(_PRIV)
    if mod is None:
        spec = importlib.util.spec_from_file_location(_PRIV, str(d / 't16_core.py'))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_PRIV] = mod
        spec.loader.exec_module(mod)
    if NEW_BRIDGE_SHA == OLD_BRIDGE_SHA or len(NEW_BRIDGE_SHA) != 64:
        raise RuntimeError('invalid T18 bridge pin')
    mod.MODULE_PINS = {**mod.MODULE_PINS, 'bridge': NEW_BRIDGE_SHA}
    mod.BRIDGE = NEW_BRIDGE_SHA
    # strict invariance: ONLY bridge changed; everything else equals the public T16.
    if mod.MODULE_PINS['bridge'] != NEW_BRIDGE_SHA or mod.MODULE_PINS['bridge'] == pub.MODULE_PINS['bridge']:
        raise RuntimeError('bridge swap failed')
    for role in ('player', 'android', 'shim', 'hwui'):
        if mod.MODULE_PINS[role] != pub.MODULE_PINS[role]:
            raise RuntimeError('T18 must not change pin ' + role)
    if not (mod.SERIAL == pub.SERIAL and mod.HOST_SHA == pub.HOST_SHA and mod.SERVER_SHA == pub.SERVER_SHA
            and mod.EXE_SHA == pub.EXE_SHA and mod.PINNED_ADDRESSES == pub.PINNED_ADDRESSES
            and set(mod.REQUIRED_MODULES) == set(pub.REQUIRED_MODULES)):
        raise RuntimeError('T18 must keep serial/tools/addresses/roles identical to T16')
    return mod


def preview():
    """Pure preview (device_calls=0): what T18 specializes, nothing more."""
    return {'execute': False, 'device_calls': 0, 'derivation': 't18-bridge-only',
            'bridge_old': OLD_BRIDGE_SHA, 'bridge_new': NEW_BRIDGE_SHA,
            'unchanged': ['player', 'android', 'shim', 'hwui', 'addresses', 'serial', 'host', 'server', 'guard'],
            'candidate': '$HOME/.local/share/westlake/t18-production/production-01/candidate.so',
            'abi_review': 'base5 in progress', 'arbitrary_pin_interface': False,
            'note': 'single AudioTrack-getter object; baseline re-link exact d4fa. Deploy on video_plan notify.'}


def entry(admission, out, port, r13_dir, t16_dir):
    """Run inside the pinned SDK15 host python. Identical to t16_observer.entry except the admission gate uses
    the T18 bridge pin; the reused R13 Session + injected 5cd Guard are unchanged."""
    _verify_source(t16_dir)
    t18core = load_t18_core(t16_dir)
    import t16_observer
    r13core, r13observer = t16_observer.load_r13(r13_dir)
    import lldb
    a = json.loads(Path(admission).read_text())
    t18core.t16_validate(a)                                   # the ONLY substantive change: T18 bridge pin
    T18Session = t16_observer.make_session_class(r13observer)
    s = T18Session(lldb, lldb.debugger, a, out, guard_factory=t16_observer.make_guard(r13_dir))
    s.result['derivation'] = 't18-bridge-dca530eb'
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
