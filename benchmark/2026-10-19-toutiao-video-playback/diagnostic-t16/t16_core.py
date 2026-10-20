"""T16 5cd post-load ANW sampler — admission. Reuses R13 device glue (t16_observer) + a 5cd Guard
(t16_identity). Tightened per base5: exact pinned address triples (not self-reported), required modules
with ACTUAL local-SHA verification, no 61b/historical profile, tools pinned to the 5cd-proven host/server.
Contract fields are never accepted as their own proof."""
import hashlib, os, re, time
from pathlib import Path

SERIAL = '5cd1e3dd00000000000000000923012c'
HOST_SHA = 'c6008509f6b4bd8b5766eaad671738364eaa01a039db00e5d94e47204972dbf1'
SERVER_SHA = '13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a'   # NDK r23b static, 5cd HW-proven
FORBIDDEN_SERVER = 'd6d9a233fd3b9bd2ff60a69eec78aa2e70eaf4d94b98e0cbb55fae90706fb229'  # old incompatible SDK15 server
HOST_UID = 20011300
EXE_SHA = 'a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'   # appspawn-x (parent+child clone)
# module SHA pins (R13 set). base5 finalizes the exact R8 module SHAs; player pivot below.
MODULE_PINS = {
    'player': '0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471',
    'android': '76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727',
    'shim': '85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a',
    'bridge': 'd4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b',
    'hwui': 'a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2',
}
REQUIRED_MODULES = set(MODULE_PINS)   # COMPLETE R13 role set (base5 pt.3): player/android/shim/bridge/hwui
PLAYER_R13 = MODULE_PINS['player']    # 0b4d95c5 — the player the pinned triples were REA-derived for
ANDROID, SHIM, BRIDGE, HWUI = MODULE_PINS['android'], MODULE_PINS['shim'], MODULE_PINS['bridge'], MODULE_PINS['hwui']
PLAYER_5CD = 'b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02'   # 5cd-deployed (T11 baseline)
# EXACT proven address triples (slot, expected_elf, pc), keyed by player SHA. Only the player these were
# REA-derived for is admitted; a different player must be added here with its own re-derived triples
# (not self-reported). shim lock pc 0x5e48 lives in the shim and is player-independent.
PINNED_ADDRESSES = {
    MODULE_PINS['player']: {'android': (0x472688, 0x3b9c, 0x3bd4), 'shim': (0x472490, 0x5e48, 0x5e48)},
}
HIST = {'boot': '0525bb05-f714-42ad-90f0-ecdb10356c4f', 'parent': 19163, 'child': 1601}
OBJECT_SCOPE = {'magic', 'tag', 'handle', 'winner_module'}


class Refuse(RuntimeError):
    pass


def need(ok, msg):
    if not ok:
        raise Refuse(msg)


def _posint(v):
    return type(v) is int and v > 0


def _verify_file(path, expect, label):
    """SHA-verify an ACTUAL local file against a pin. Missing/unreadable => Refuse (a declared-correct
    sha256 field with a nonexistent path must never pass — base5 pt.3)."""
    try:
        got = hashlib.sha256(Path(os.path.expandvars(os.path.expanduser(path))).resolve().read_bytes()).hexdigest()
    except OSError as ex:
        raise Refuse('local file unreadable ' + label + ': ' + str(ex))
    need(got == expect, 'actual local SHA mismatch ' + label)


def t16_validate(a, now=None, files=True):
    """Judge a T16 admission. Structural pins are checked first; with files=True the ACTUAL local tool and
    module bytes are SHA-verified LAST (self-reported sha256 fields are never trusted as their own proof).
    This is only the offline admission gate — the reused R13 Session.Guard runs the original on-device
    bookended identity/module gate after admission. Raises Refuse on any violation."""
    now = time.time() if now is None else now
    need(a.get('schema') == 't16-admission-v1' and a.get('execution_enabled') is True
         and a.get('approved_by') == 'outer(codex)', 'authorization')
    need(a.get('serial') == SERIAL, 'serial must be 5cd (not 61b)')
    need(type(a.get('created_at')) in (int, float) and 0 <= now - a['created_at'] <= 300, 'stale admission')
    need(type(a.get('expires_at')) in (int, float) and now < a['expires_at'] <= a['created_at'] + 1800, 'expiry')
    need(a.get('max_seconds', 120) == 120 and a.get('max_fromSurface', 4) == 4 and a.get('max_lock', 4) == 4, 'budget override')
    # tools — pinned pair; forbid the old incompatible server; sha FIELDS present (local bytes verified last)
    need(a.get('host', {}).get('sha256') == HOST_SHA, 'host must be SDK15 c6008509')
    srv = a.get('server', {})
    need(srv.get('sha256') == SERVER_SHA and srv.get('sha256') != FORBIDDEN_SERVER, 'server must be NDK r23b 13c0b4bf, never d6d9a233')
    need(_posint(srv.get('pid')) and _posint(srv.get('birth')) and type(srv.get('uid')) is int and srv.get('uid') >= 0,
         'server identity (pid/birth>0, uid int>=0 — independent lldb-server may be root; Guard does the on-device UID check)')
    need(a.get('require_hardware_breakpoint') is True and a.get('hardware_explicit') is True, 'hardware-only')
    for f in ('no_software_fallback', 'no_stepout', 'no_expr'):
        need(a.get(f) is True, f + '!=true')
    need(isinstance(a.get('holder'), str) and a['holder'] and '\n' not in a['holder'], 'holder')
    for tool in ('host', 'hdc', 'lock_script'):
        need(re.fullmatch('[0-9a-f]{64}', a.get(tool, {}).get('sha256', '')) is not None, 'tool sha field ' + tool)
    # identity — FRESH post-restart profile, never historical; parent UID exactly 0; exe pins EXACT
    e = a.get('identity', {})
    need(re.fullmatch(r'[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}', e.get('boot', '')) is not None, 'boot uuid')
    need(e['boot'] != HIST['boot'] and e.get('parent') != HIST['parent'] and e.get('child') != HIST['child'],
         'historical profile refused — fresh post-restart identity required')
    for k in ('parent', 'parent_birth', 'child', 'child_birth', 'uid'):
        need(_posint(e.get(k)), 'identity int ' + k)
    need(e['child'] != e['parent'] and e['uid'] == HOST_UID, 'host UID 20011300')
    need(e.get('parent_uid') == 0, 'parent UID must be exactly 0')
    need(srv['pid'] != e['parent'] and srv['pid'] != e['child'], 'server pid must differ from the business parent/child pid')
    for k in ('parent_exe_sha256', 'child_exe_sha256'):
        need(e.get(k) == EXE_SHA, 'exe pin must equal appspawn-x EXE_SHA (not merely hex): ' + k)
    need(e.get('fresh_profile') is True and re.fullmatch(r'mnt:\[[0-9]+\]', e.get('mnt', '')) is not None, 'fresh profile + mnt ns')
    # modules — COMPLETE R13 role set, each pinned, with dev/inode + remote_path (local bytes verified last)
    mods = a.get('modules', {})
    need(set(mods) == REQUIRED_MODULES, 'modules must be exactly the R13 set ' + str(sorted(REQUIRED_MODULES)))
    for k, m in mods.items():
        need(m.get('sha256') == MODULE_PINS[k], 'module pin ' + k)
        need(_posint(m.get('device')) and _posint(m.get('inode')), 'module dev/inode ' + k)
        need(isinstance(m.get('remote_path'), str) and m['remote_path'].startswith('/data/')
             and not any(c in m['remote_path'] for c in '\n\r\x00'), 'module remote_path ' + k)
    # player pivot + EXACT pinned triples; EXACTLY len(want) rows, no duplicate-role masking
    pl = mods['player']['sha256']
    need(pl in PINNED_ADDRESSES, 'player SHA has no proven pinned address triples (base5 must pin it)')
    want = PINNED_ADDRESSES[pl]
    addr = a.get('addresses')
    need(isinstance(addr, list) and len(addr) == len(want), 'addresses must be exactly ' + str(len(want)) + ' rows (no set-masking)')
    seen = set()
    for x in addr:
        role = x.get('role')
        need(role in want and role not in seen, 'address role must be a unique pinned role: ' + str(role))
        seen.add(role)
        need((x.get('slot'), x.get('expected_elf'), x.get('pc')) == want[role], 'address triple must equal the proven pin for ' + role)
    # scope + no R15 masquerade
    extra = set(a.get('observed_fields', sorted(OBJECT_SCOPE))) - OBJECT_SCOPE
    need(not extra, 'out-of-scope observation ' + str(sorted(extra)))
    need(not a.get('installs_r15'), 'R15 OFFLINE_ADAPTER_ONLY must not be installed/masqueraded')
    # ACTUAL local bytes LAST — never trust the self-reported sha256 fields
    if files:
        _verify_file(a['host']['path'], HOST_SHA, 'host')
        _verify_file(a['hdc']['path'], a['hdc']['sha256'], 'hdc')
        _verify_file(a['lock_script']['path'], a['lock_script']['sha256'], 'lock_script')
        for k, m in mods.items():
            _verify_file(m['local_path'], MODULE_PINS[k], 'module ' + k)
    return a


def plan_preview():
    """Pure preview object (device_calls=0)."""
    return {'execute': False, 'device_calls': 0, 'serial': SERIAL, 'schema': 't16-admission-v1',
            'host_sha256': HOST_SHA, 'server_sha256': SERVER_SHA, 'forbidden_server': FORBIDDEN_SERVER,
            'required_modules': sorted(REQUIRED_MODULES), 'pinned_players': sorted(PINNED_ADDRESSES),
            'shim_lock_pc': '0x5e48', 'winner_pc': '0x3bd4',
            'object_gate': {'magic@0': '0x5f776e64', 'tag@0xc8': '0x414e5731', 'handle@0xc0': 8},
            'observed_fields': sorted(OBJECT_SCOPE), 'refuse_historical': HIST, 'host_uid': HOST_UID,
            'playback': 'UNKNOWN_NOT_TESTED', 'needs_outer_review': True,
            'note': 'base5 supplies the exact R8 player SHA + re-derived triples if != 0b4d95c5; validate verifies ACTUAL local SHAs'}
