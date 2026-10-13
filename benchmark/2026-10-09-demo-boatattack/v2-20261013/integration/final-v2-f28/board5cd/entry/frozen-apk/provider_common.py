"""Pinned local inputs and the existing BMS transport; no board writer here."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex

WS = Path(os.environ.get('WORKSPACES', str(Path(__file__).resolve().parents[3])))
SERIALS = {'61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c', '5ea34a4500000000000000001123012c'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(value, base):
    p = Path(value.replace('$WORKSPACES/', str(WS) + '/', 1))
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def pinned(pin, base, name):
    if not isinstance(pin, dict) or not isinstance(pin.get('path'), str) or not pin['path']:
        raise ValueError(name + ' requires typed {path,sha256}')
    p = resolve(pin['path'], base)
    if not re.fullmatch('[0-9a-f]{64}', str(pin.get('sha256', ''))) or digest(p) != pin['sha256']:
        raise ValueError(name + ' SHA drift')
    return p


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def context(args, own, apk=False):
    base = Path(args.deployment).resolve().parent
    dep = json.loads(Path(args.deployment).read_text())
    seal = json.loads(Path(args.seal).read_text())
    if dep.get('schema') != 'demo-restore-deployment/v1' or seal.get('schema') != 'demo-seal/v1':
        raise ValueError('wrong seal/deployment schema')
    if args.serial not in SERIALS or seal.get('serial') != args.serial:
        raise ValueError('wrong seal/requested serial')
    if dep.get('synthetic') or seal.get('synthetic'):
        raise ValueError('synthetic material cannot execute providers')
    providers = [p for p in dep.get('providers', []) if p.get('layer') == 'u13']
    if len(providers) != 1:
        raise ValueError('exactly one u13 provider required')
    prov = providers[0]
    cfg = prov.get('apk_install') if apk else prov
    if not isinstance(cfg, dict):
        raise ValueError('apk_install must be a typed object')
    if pinned(cfg.get('program'), base, 'program') != Path(own).resolve():
        raise ValueError('program self-pin points to another file')
    if pinned(cfg.get('common'), base, 'common') != Path(__file__).resolve():
        raise ValueError('common helper identity mismatch')
    exe = pinned(cfg.get('executor'), base, 'executor')
    if Path(args.out).exists():
        raise ValueError('output already exists')
    if not isinstance(prov.get('boot_id'), str) or not re.fullmatch('[0-9a-f-]{36}', prov['boot_id']):
        raise ValueError('boot_id required from current board evidence')
    if prov.get('serial') != args.serial:
        raise ValueError('provider serial mismatch')
    return base, dep, seal, prov, cfg, exe


def board_for(exe, cfg, prov, args, out):
    b = module(exe, 'pinned_master_batch')
    transport = prov.get('transport') or {}
    if not all(isinstance(transport.get(k), str) and transport[k] for k in ('hdc_cmd', 'lock_cmd', 'lane')):
        raise ValueError('transport requires hdc_cmd/lock_cmd/lane')
    board = b.Board(args.serial, transport['hdc_cmd'], transport['lock_cmd'], transport['lane'], out / 'commands')
    board.ready()
    if board.boot.strip() != prov['boot_id']:
        raise ValueError('current boot differs from reviewed provider boot_id')
    return b, board


def read(board, command):
    rc, value = board.shell(command, required=False)
    if rc:
        raise ValueError('read failed rc=' + str(rc) + ': ' + command)
    return value.strip()


def path_hash(board, path):
    if not re.fullmatch('/[A-Za-z0-9_./:+@-]+', path) or '..' in path.split('/'):
        raise ValueError('unsafe target path')
    # Missing is accepted only with readable/searchable parent; no transport
    # failure, denied ancestor or broken symlink may become an install request.
    q = shlex.quote(path)
    parent = shlex.quote(str(Path(path).parent))
    command = f'if [ -f {q} ]; then sha256sum {q}; elif [ ! -e {q} ] && [ ! -L {q} ]; then p={parent}; while [ ! -e "$p" ] && [ ! -L "$p" ] && [ "$p" != / ]; do p=$(dirname "$p"); done; if [ -d "$p" ] && [ -r "$p" ] && [ -x "$p" ]; then echo VERIFIED_ABSENT; else exit 42; fi; else exit 42; fi'
    text = read(board, command)
    if text == 'VERIFIED_ABSENT':
        return None
    match = re.fullmatch(r'([0-9a-f]{64})\s+' + re.escape(path), text)
    if not match:
        raise ValueError('unparseable hash observation: ' + path)
    return match[1]


def save(out, data):
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
