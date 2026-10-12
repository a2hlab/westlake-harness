#!/usr/bin/env python3
"""Route B standard-argv restoration adapter; original 9436/b093 never modified.

STANDARD: --seal S --serial SERIAL --deployment D --out F
OFFLINE:  --compile --binding B --out NEW_PACKAGE
TEST:     --self-test (isolated local files, never a device)

The provider owns Route B only. U13, host-HAP installation and demo-APK
installation belong to t4. An installed, hash-verified HAP and its actual
per-board UID are prerequisites, not guessed from the 61b archive. Runtime221
is a byte source, not permission/preimage authority. All runtime metadata,
existing ancestor checks and new control preimages must come from the target.

Compilation emits a NEW reviewed derivative, exact diffs, member hashes and a
complete plan. It changes only executor SERIAL/ROOT/explicit target constants;
all original transaction, metadata, backup, partial-send, CFG trap and
cooperative-stop guards remain. Deployment requires independently pinned
authorization -> complete generated plan and outer-reviewed manifest. No
default-namespace/runtime patch, reboot, init start, UI or signing is performed.

Binding schema route-b-restore-binding/v1:
  serial, boot_id, host_uid, runtime_root, stage_root, socket, attempt_root;
  release_inventory{path,sha256}, runtime_archive{path,sha256}, host_hap{path,sha256};
  before{target:exact metadata/absence proof}, after{target:mode/uid/gid/label};
  directories (new candidate root only), preserved (old stop only), tools;
  stage_files[{source pin,target,after,before}], required_directories;
  prerequisites (already installed HAP/unchanged binaries; exact target+SHA);
  startup_enabled=false by default. No boot/PID/WID in durable startup authority.

Deployment provider fields:
  layer=toutiao-route-b, program{this file,pin}, targets;
  prepared{path,manifest_sha256}, action=apply|rollback,
  authorization{path,sha256}, transaction_dir (rollback only).
  execution_enabled=false previews without transport. True never previews and
  returns the actual derived executor rc; missing fields reject before transport.
  Ordinary demo_restore supplies the write authorization/lock; this adapter
  additionally verifies the held holder and its own fresh boot inside transaction.

Installation auth signer outer(codex) is deliberately distinct from the legacy
demo_restore rehearsal signer literal outer(claude). Neither is manufactured.
"""
import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import importlib.util
import contextlib
import io

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[2])))
RELEASE = HERE.parent / '2026-10-12-recovery-executor'
ALIASES = HERE.parent / '2026-10-12-recovery-exe-alias'
OLD_SERIAL = '61b0657200000000000000000324012c'
SERIALS = {OLD_SERIAL, '5cd1e3dd00000000000000000923012c'}
OLD_UID = 20011206
OLD_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview'
OLD_RT = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
OLD_STAGE = '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d'
OLD_SOCKET = '/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002'
CFG = '/system/etc/init/01_westlake_u13_toutiao.cfg'
OLD_STOP = '/data/local/tmp/operator45/selfheal48/stop'
EXECUTOR_SHA = '430fbf4a6348dc12ef107c4786a16de83c06a99330cd527c5dbbbc6aca44f30a'
HAP_SHA = 'df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a'
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def write(p, value):
    p = Path(p)
    with p.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def resolve(value, base):
    need(isinstance(value, str) and value, 'missing path')
    value = value.replace('$WORKSPACES/', str(WS) + '/', 1)
    value = os.path.expandvars(value)
    p = Path(value)
    return p.resolve() if p.is_absolute() else (Path(base) / p).resolve()


def pin(value, base):
    need(isinstance(value, dict) and SHA.fullmatch(value.get('sha256', '')),
         'missing exact SHA pin')
    p = resolve(value.get('path'), base)
    need(p.is_file() and digest(p) == value['sha256'], 'source SHA drift: ' + str(p))
    return p


def safe_path(value):
    need(isinstance(value, str) and re.fullmatch(r'/[A-Za-z0-9_./:+@-]+', value)
         and '..' not in value.split('/'), 'unsafe board path')
    return value


def metadata(value):
    need(isinstance(value, dict), 'metadata missing')
    need(isinstance(value.get('mode'), str) and re.fullmatch(r'[0-7]{3,4}', value['mode']), 'mode missing')
    for k in ('uid', 'gid'):
        need(type(value.get(k)) is int and 0 <= value[k] < 2**31, k + ' missing')
    need(isinstance(value.get('label'), str) and re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0', value['label']), 'label missing')


def before_image(value, base):
    need(isinstance(value, dict) and type(value.get('exists')) is bool, 'preimage missing')
    if value['exists']:
        metadata(value)
        need(SHA.fullmatch(value.get('sha256', '')), 'preimage SHA missing')
        p = resolve(value.get('source'), base)
        need(p.is_file() and digest(p) == value['sha256'], 'preimage bytes missing/drift')
    else:
        need(isinstance(value.get('proof'), str) and value['proof'], 'absence proof missing')


def verify_inventory(p, base):
    j = read(p)
    rows = j.get('files')
    need(isinstance(rows, list) and rows, 'empty release inventory')
    for row in rows:
        f = resolve(row['path'], base)
        need(f.is_file() and digest(f) == row['sha256'] and f.stat().st_size == row['bytes'],
             'inventory drift: ' + row['path'])


def board_binding(b):
    need(b.get('schema') == 'route-b-restore-binding/v1', 'wrong binding schema')
    need(b.get('serial') in SERIALS, 'unsupported board')
    need(isinstance(b.get('boot_id'), str) and BOOT.fullmatch(b['boot_id']), 'fresh boot missing')
    need(type(b.get('host_uid')) is int and 20000000 <= b['host_uid'] < 30000000,
         'actual installed host UID missing')
    rt = safe_path(b.get('runtime_root'))
    match=re.fullmatch(r'/data/app/el2/100/base/org\.westlake\.imehost/files/a2hlab-source-([0-9a-f]{32})',rt)
    need(match,'foreign runtime')
    need(safe_path(b.get('stage_root'))=='/data/local/tmp/a2hlab-app-'+match[1], 'foreign stage')
    # The captured Route B socket uses the first20 profile characters; the
    # runtime/stage directory names use all32. Do not invent a new socket name.
    need(safe_path(b.get('socket'))=='/dev/unix/socket/A2HSource'+match[1][:20], 'foreign socket')
    root = safe_path(b.get('attempt_root'))
    need(root.startswith('/data/westlake-demo/toutiao/recovery-attempts/') and root != OLD_ROOT,
         'new independent attempt required')
    need(root.count('/') == OLD_ROOT.count('/'), 'nested attempt')
    need(type(b.get('startup_enabled', False)) is bool, 'startup flag must be boolean')


def derive_text(raw, binding):
    # Exact known constants only; no fuzzy patch, arbitrary regex or user data.
    text = raw.decode()
    for old, new in [(OLD_ROOT, binding['attempt_root']), (OLD_SERIAL, binding['serial']),
                     (OLD_RT, binding['runtime_root']), (OLD_STAGE, binding['stage_root']),
                     (OLD_SOCKET, binding['socket'])]:
        text = text.replace(old, new)
    text = text.replace(str(OLD_UID), str(binding['host_uid']))
    return text.encode()


def ancestor_of(target, child):
    return child.startswith(target.rstrip('/') + '/')


def storage_directories(b, targets):
    """Typed absent storage roots; exact creation list derived from member paths.

    No guessed metadata. Existing installed HAP ancestors are read-only guards.
    Empty new runtime/stage directories are removable on rollback; candidate
    attempt/log/stop directories are retained. Never touch app-data/data/webview.
    """
    out = []
    for root, kind in ((b['runtime_root'],'runtime'),(b['stage_root'],'stage')):
        state = b['storage'][kind]
        need(state.get('exists') is False and state.get('proof'), 'absent '+kind+' root proof required')
        metadata(state.get('after'))
        names = {root}
        for t in targets:
            if not ancestor_of(root,t):continue
            parent = str(Path(t).parent)
            while parent != root:
                names.add(parent);parent=str(Path(parent).parent)
        for name in sorted(names,key=lambda s:(s.count('/'),s)):
            out.append({'target':name,'before':{'exists':False,'proof':state['proof']},'after':state['after']})
    extra=b.get('additional_directories',[])
    allowed={str(Path(b['runtime_root']).parent),'/data/westlake-demo',
        '/data/westlake-demo/toutiao','/data/westlake-demo/toutiao/scripts',
        '/data/local/tmp/operator45','/data/local/tmp/operator45/selfheal48'}
    for d in extra:
        need(d.get('target') in allowed and d.get('before',{}).get('exists') is False and d['before'].get('proof'),
             'unapproved new Route B ancestor')
        metadata(d['after']);out.append(d)
    need(len({r['target'] for r in out})==len(out),'duplicate storage directory')
    return sorted(out,key=lambda d:(d['target'].count('/'),d['target']))


def new_executor(source, b, allowed, directories):
    """Explicit derivative of immutable b093; additions are narrow audited guards.

    No dynamic import/global override. The generated program's complete bytes
    are in manifest.json and are independently pinned by the install ticket.
    """
    changed = source.replace("SERIAL='"+OLD_SERIAL+"'",'SERIAL='+repr(b['serial']),1)
    changed = changed.replace("ROOT='"+OLD_ROOT+"'",'ROOT='+repr(b['attempt_root']),1)
    anchor="SHA=re.compile(r'[0-9a-f]{64}\\Z')"
    need(source.count(anchor)==1,'executor constant anchor drift')
    newdirs=sorted(r['target'] for r in directories)
    changed=changed.replace(anchor,'EXTERNAL_CONTROLS.update('+repr(sorted(allowed))+')\n'
        +'RESTORE_STORAGE_DIRS=set('+repr(newdirs)+')\n'+anchor,1)
    old="directory['target'] in {ROOT, str(Path(ROOT).parent)} and directory['before']['exists'] is False"
    need(changed.count(old)==1,'directory validator anchor drift')
    changed=changed.replace(old,"directory['target'] in ({ROOT, str(Path(ROOT).parent)} | RESTORE_STORAGE_DIRS) and directory['before']['exists'] is False",1)
    anchor='def fresh(dev,plan):\n    check_identity(dev,plan)\n'
    need(changed.count(anchor)==1,'fresh guard anchor drift')
    guard='''    for d in plan.get('directory_prerequisites',[]):
        m=d['after']; path=d['target']
        got=dev.shell('existing-host-directory', 'set -eu; test -d '+q(path)+'; test ! -L '+q(path)+"; stat -c '%a:%u:%g' "+q(path)+'; ls -ldnZ '+q(path))
        require(got.splitlines()[0]==m['mode']+':'+str(m['uid'])+':'+str(m['gid']) and m['label'] in got.splitlines()[1].split(),'installed host directory drift')
'''
    changed=changed.replace(anchor,anchor+guard,1)
    # The ordinary file writer cannot silently mkdir unrecorded ancestors here.
    old="dev.shell('mkdir-control','set -eu; mkdir -p '+q(str(Path(target).parent)))"
    need(changed.count(old)==1,'parent directory anchor drift')
    changed=changed.replace(old,"dev.shell('parent-directory-read','set -eu; test -d '+q(str(Path(target).parent))+'; test ! -L '+q(str(Path(target).parent)))",1)
    # Restore-stage directory cleanup is only after all original rollback guards.
    anchor='if not receipt.exists():save(receipt,'
    need(changed.count(anchor)==1,'rollback cleanup anchor drift')
    start=changed.index(anchor);end=changed.index('\n',start)
    changed=changed[:end]+'''
    for d in reversed(plan.get('storage_directories',[])):
        check_identity(dev,plan); path=d['target']; m=d['after']
        dev.shell('remove-empty-owned-storage-directory','set -eu; if [ -e '+q(path)+' ]; then test -d '+q(path)+'; test ! -L '+q(path)+"; test \\"$(stat -c '%a:%u:%g' "+q(path)+")\\" = "+q(m['mode']+':'+str(m['uid'])+':'+str(m['gid']))+'; ls -ldnZ '+q(path)+' | grep -F '+q(m['label'])+' >/dev/null; rmdir '+q(path)+'; fi')
'''+changed[end:]
    compile(changed,'derived-executor.py','exec')
    return changed


def compile_package(binding_path, out):
    b = read(binding_path)
    base = Path(binding_path).resolve().parent
    board_binding(b)
    inv = pin(b['release_inventory'], base)
    verify_inventory(inv, inv.parents[2])
    need(digest(RELEASE / 'executor.py') == EXECUTOR_SHA, 'immutable executor drift')
    hap = pin(b['host_hap'], base)
    need(digest(hap) == HAP_SHA, 'host HAP differs from deployed host')
    archive = pin(b['runtime_archive'], base)
    index = read(archive)
    need(len(index.get('files', [])) == 221, 'runtime archive must have 221 members')
    out = Path(out).resolve()
    need(not out.exists(), 'new package output required')
    need(not out.is_relative_to(RELEASE.resolve()), 'cannot write original release')
    alias_manifest=pin(b['exe_alias_manifest'],base)
    verify_inventory(alias_manifest,alias_manifest.parents[2])
    alias_root=alias_manifest.parent/'candidate'
    for name in ('launch-common.sh','watchdog.sh','route-b-owner.sh'):
        need((alias_root/name).is_file(),'accepted alias member missing')
    # All input metadata/local bytes checked before creating package.
    rows = []
    seen = set()
    for a in index['files']:
        old = safe_path(a['target'])
        need(old.startswith(OLD_RT + '/'), 'foreign archive target')
        suffix = old[len(OLD_RT) + 1:]
        need(not set(suffix.split('/')) & {'app-data', 'data', 'webview', 'cache'}, 'user-state archive member')
        target = b['runtime_root'] + '/' + suffix
        need(target not in seen, 'duplicate archive target')
        seen.add(target)
        source = pin({'path': a['source'], 'sha256': a['sha256']}, base)
        meta=b['storage']['runtime']['file_after']
        before={'exists':False,'proof':b['storage']['runtime']['proof']}
        metadata(meta); before_image(before, base)
        rows.append((target, suffix, source, meta, before))
    for s in b.get('stage_files', []):
        target = safe_path(s['target'])
        need(target.startswith(b['stage_root'] + '/') and target not in seen, 'stage target outside route')
        need(not set(target[len(b['stage_root'])+1:].split('/')) & {'app-data', 'data', 'webview', 'cache'}, 'user stage path')
        metadata(s['after']); before_image(s['before'], base)
        source = pin(s['source'], base)
        seen.add(target); rows.append((target, 'stage/' + Path(target).name, source, s['after'], s['before']))
    need({Path(s['target']).name for s in b.get('stage_files', [])} >=
         {'source_app_namespace', 'host_spawn', 'request.bin'}, 'actual stage tools/request missing')
    preserved = b.get('preserved')
    need(isinstance(preserved, list) and len(preserved) == 1 and preserved[0]['target'] == OLD_STOP,
         'historical stop binding required')
    before_image(preserved[0]['before'], base)
    oldplan = read(RELEASE / 'plan.disabled.json')
    for m in oldplan['members']:
        target = m['target'].replace(OLD_ROOT, b['attempt_root'])
        metadata(b['after'].get(target)); before_image(b['before'].get(target), base)
    for directory in b['required_directories']:
        safe_path(directory['target']); metadata(directory['after'])
        need(directory.get('exists') is True, 'existing runtime/stage ancestor required; HAP initializer is t4')
    need(any(d['target'] in {str(Path(b['runtime_root']).parent),str(Path(b['runtime_root']).parent.parent)} and d['after']['uid']==b['host_uid']
         for d in b['required_directories']),'installed host directory must match actual UID')
    need(b.get('prerequisites') and any(p['target'] == '/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
         and p['sha256'] == HAP_SHA for p in b['prerequisites']), 'installed host HAP prerequisite missing')
    for tool in b['tools'].values(): pin(tool, base)
    storage=storage_directories(b,seen)
    all_dirs=b['directories']+storage
    newnames={d['target'] for d in all_dirs};existing={d['target'] for d in b['required_directories']}
    need(len(newnames)==len(all_dirs),'duplicate directory creation')
    for d in all_dirs:
        need(d['before']['exists'] is False and d['before'].get('proof'),'new directory absence not proven')
        metadata(d['after'])
    for target in seen | {m['target'].replace(OLD_ROOT,b['attempt_root']) for m in oldplan['members']} | newnames:
        need(str(Path(target).parent) in (newnames|existing),'undeclared parent directory: '+str(Path(target).parent))
    out.mkdir(); (out / 'payload').mkdir(); (out / 'runtime').mkdir()
    changes = []
    for p in sorted((RELEASE / 'payload').iterdir()):
        if not p.is_file(): continue
        raw = (alias_root/p.name).read_bytes() if p.name in {'launch-common.sh','watchdog.sh','route-b-owner.sh','entry.sh'} else p.read_bytes()
        data = derive_text(raw, b) if p.suffix in {'.sh', '.cfg', '.env'} else raw
        (out / 'payload' / p.name).write_bytes(data)
        if data != raw:
            changes.append({'path': 'payload/' + p.name, 'before_sha256': digest(p),
                            'after_sha256': hashlib.sha256(data).hexdigest(),
                            'diff': ''.join(difflib.unified_diff(raw.decode().splitlines(True), data.decode().splitlines(True)))})
    plan = copy.deepcopy(oldplan)
    plan.update(serial=b['serial'], boot_id=b['boot_id'], execution_enabled=b.get('startup_enabled', False),
                preserved=copy.deepcopy(preserved), tools=b['tools'], prerequisites=b['prerequisites'],
                directories=sorted(all_dirs,key=lambda d:(d['target'].count('/'),d['target'])), storage_directories=storage,
                directory_prerequisites=b['required_directories'])
    plan['tools']={k:{'path':str(pin(v,base)),'sha256':v['sha256']} for k,v in b['tools'].items()}
    for row in plan['preserved']:
        if row['before']['exists']:row['before']['source']=str(resolve(row['before']['source'],base))
    for m in plan['members']:
        m['target'] = m['target'].replace(OLD_ROOT, b['attempt_root'])
        m['before'] = b['before'][m['target']]; m['after'] = b['after'][m['target']]
        if m['before']['exists']: m['before']['source'] = str(resolve(m['before']['source'], base))
    for target, suffix, source, meta, before in rows:
        data = source.read_bytes()
        if suffix in {'run.sh', 'prepare_jit50.sh', 'preseed_metasec48.sh'}:
            data = derive_text(data.replace(b'20010053', str(b['host_uid']).encode()), b)
            if suffix == 'run.sh':
                text, n = re.subn(r'export WL_PARENT_ID=[0-9]+', 'export WL_PARENT_ID=0', data.decode())
                need(n == 1, 'run.sh WID template must have one field'); data = text.encode()
        if suffix == 'stage/request.bin':
            need(len(data) == 672, 'actual request size')
            buf = bytearray(data)
            for pos in (312, 316):struct.pack_into('<I', buf, pos, b['host_uid'])
            data = bytes(buf)
        dst = out / 'runtime' / suffix
        dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data)
        before = copy.deepcopy(before)
        if before['exists']: before['source'] = str(resolve(before['source'], base))
        plan['members'].append({'target': target, 'source': '$PACKAGE/runtime/' + suffix,
                                'sha256': digest(dst), 'before': before, 'after': meta})
        if data != source.read_bytes():
            changes.append({'path': str(dst.relative_to(out)), 'before_sha256': digest(source),
                            'after_sha256': digest(dst), 'derivation': 'exact UID/path fields; WID=0 until fresh host window; request LE312/316'})
    # Derived per-board executor: all other b093 guard/transaction code unchanged.
    code = (RELEASE / 'executor.py').read_text()
    changed = new_executor(code,b,seen,storage)
    (out / 'executor.py').write_text(changed)
    changes.append({'path': 'executor.py', 'before_sha256': EXECUTOR_SHA, 'after_sha256': digest(out / 'executor.py'),
                    'diff': ''.join(difflib.unified_diff(code.splitlines(True), changed.splitlines(True)))})
    # The independently accepted alias entry pins the actual derived watchdog/helper.
    entry=out/'payload/entry.sh';entry_text=entry.read_text()
    for name in ('watchdog.sh','route-b-owner.sh'):
        oldpin=digest(alias_root/name);need(entry_text.count(oldpin)==1,'entry pin drift: '+name)
        entry_text=entry_text.replace(oldpin,digest(out/'payload'/name))
    entry.write_text(entry_text)
    # Build the per-boot file manifest from actual NEW bytes, never stale originals.
    manifest_rows = []
    for line in (alias_root/'members.tsv').read_text().splitlines():
        _, name, mode = line.split(); p = out / 'payload' / {'start-parent.sh':'start-parent-prepared.sh', 'spawn.sh':'spawn-prepared.sh', 'screen-gate':'screen-gate-feed'}.get(name, name)
        manifest_rows.append(digest(p) + ' ' + name + ' ' + mode)
    (out / 'payload/members.tsv').write_text('\n'.join(manifest_rows) + '\n')
    config = (out / 'payload/startup.env').read_text()
    fields = {'STARTUP_APPROVED_BY': 'outer(codex)' if b.get('startup_enabled', False) else 'PENDING',
              'STARTUP_ENABLED': '1' if b.get('startup_enabled', False) else '0',
              'STARTUP_MEMBERS_SHA': digest(out / 'payload/members.tsv'),
              'STARTUP_START_PARENT_SHA': digest(out / 'payload/real-start-parent-bounded.sh')}
    by_name = {Path(m['target']).name: m['sha256'] for m in plan['members']}
    for key, name in [('STARTUP_JIT_SHA','prepare_jit50.sh'), ('STARTUP_REQUEST_SHA','request.bin'),
                      ('STARTUP_NAMESPACE_SHA','source_app_namespace'),('STARTUP_HOST_SPAWN_SHA','host_spawn')]:fields[key]=by_name[name]
    for key, value in fields.items():
        config, n = re.subn('^' + key + "='[^']*'", key + '=' + repr(value), config, flags=re.M)
        need(n == 1, 'startup field drift: ' + key)
    old_before = preserved[0]['before']
    config = re.sub(r"^STARTUP_OLD_STOP_SHA='[^']*'", 'STARTUP_OLD_STOP_SHA=' + repr(old_before.get('sha256','NONE')), config, flags=re.M)
    if not old_before['exists']:
        p = out / 'payload/config-common.sh'; text = p.read_text()
        text = text.replace('[ -f "$old" ] && [ ! -L "$old" ] || fail HISTORICAL_STOP_CHANGED\n[ "$(sha256sum "$old" | cut -d\' \' -f1)" = "$STARTUP_OLD_STOP_SHA" ] || fail HISTORICAL_STOP_SHA',
                            '[ ! -e "$old" ] && [ ! -L "$old" ] || fail HISTORICAL_STOP_CHANGED')
        p.write_text(text)
        manifest_rows = [digest(out / 'payload/config-common.sh') + ' config-common.sh 550' if ' config-common.sh ' in line else line for line in manifest_rows]
        (out / 'payload/members.tsv').write_text('\n'.join(manifest_rows) + '\n')
        config = re.sub(r"^STARTUP_MEMBERS_SHA='[^']*'", 'STARTUP_MEMBERS_SHA=' + repr(digest(out / 'payload/members.tsv')), config, flags=re.M)
    (out / 'payload/startup.env').write_text(config)
    (out / 'payload/startup.expected.sha256').write_text(digest(out / 'payload/startup.env') + '\n')
    for m in plan['members']: m['sha256'] = digest(out / m['source'].removeprefix('$PACKAGE/'))
    write(out / 'plan.json', plan)
    write(out / 'binding.json', b)
    # Include every changed/new final byte; the earlier per-file diffs are context,
    # final manifest below is the authoritative binding after startup closure.
    write(out / 'derivation.json', {'source_executor_sha256': EXECUTOR_SHA, 'changes': changes,
          'required_directories': b['required_directories'], 'plan_sha256': digest(out / 'plan.json'), 'device_calls': 0})
    files = [{'path': str(p.relative_to(out)), 'sha256': digest(p), 'bytes': p.stat().st_size}
             for p in sorted(out.rglob('*')) if p.is_file()]
    write(out / 'manifest.json', {'schema':'route-b-prepared/v1', 'serial':b['serial'], 'files':files,
          'plan_sha256':digest(out / 'plan.json'), 'requires_outer_review':True})
    return {'status':'COMPILED_NOT_AUTHORIZED', 'device_calls':0, 'manifest_sha256':digest(out / 'manifest.json'),
            'plan_sha256':digest(out / 'plan.json'), 'serial':b['serial']}


def prepared_package(ref, base, serial):
    root = resolve(ref['path'], base)
    need(root.is_dir() and SHA.fullmatch(ref.get('manifest_sha256','')), 'prepared package missing')
    need(digest(root / 'manifest.json') == ref['manifest_sha256'], 'prepared manifest drift')
    manifest = read(root / 'manifest.json')
    need(manifest['schema'] == 'route-b-prepared/v1' and manifest['serial'] == serial, 'prepared board mismatch')
    listed = set()
    for row in manifest['files']:
        name = row['path']; need(not Path(name).is_absolute() and '..' not in Path(name).parts and name not in listed, 'manifest path')
        listed.add(name); p = root / name
        need(p.is_file() and not p.is_symlink() and digest(p) == row['sha256'] and p.stat().st_size == row['bytes'], 'prepared bytes drift: ' + name)
    need({'executor.py','plan.json','binding.json','derivation.json'} <= listed, 'prepared code omitted')
    plan = read(root / 'plan.json'); binding = read(root / 'binding.json')
    board_binding(binding)
    need(plan['serial'] == serial and manifest['plan_sha256'] == digest(root / 'plan.json'), 'prepared plan mismatch')
    for m in plan['members']:
        need(m['source'].startswith('$PACKAGE/'),'member outside prepared package')
        need(m['source'].removeprefix('$PACKAGE/') in listed,'prepared member omitted')
    need(read(root / 'derivation.json')['source_executor_sha256'] == EXECUTOR_SHA, 'derivative lineage drift')
    need(digest(RELEASE/'executor.py')==EXECUTOR_SHA,'immutable base executor drift')
    # Recompute the intended derivative, not just a supplied lineage string.
    expected=new_executor((RELEASE/'executor.py').read_text(),binding,
        {m['target'] for m in plan['members'] if ancestor_of(binding['runtime_root'],m['target']) or ancestor_of(binding['stage_root'],m['target'])},
        plan['storage_directories'])
    need((root/'executor.py').read_text()==expected,'derived executable differs from narrow recipe')
    return root, plan, binding


def invoke(args, runner=subprocess.run):
    seal_path, dep_path = Path(args.seal).resolve(), Path(args.deployment).resolve()
    seal, dep = read(seal_path), read(dep_path); base = dep_path.parent
    need(args.serial in SERIALS, 'unsupported serial')
    need(dep.get('schema') == 'demo-restore-deployment/v1' and seal.get('schema') == 'demo-seal/v1', 'standard documents schema')
    candidates = [p for p in dep.get('providers',[]) if p.get('layer') == 'toutiao-route-b']
    need(len(candidates) == 1, 'one Route B provider required')
    provider = candidates[0]
    need(pin(provider['program'],base) == Path(__file__).resolve(), 'adapter self pin mismatch')
    package, plan, binding = prepared_package(provider['prepared'],base,args.serial)
    expected = {target:sha for members in seal['files'].values() for target,sha in members.items()}
    members = {r['target']:r['sha256'] for r in plan['members']}
    need(set(provider['targets']) == set(members), 'provider targets differ from actual plan')
    need(all(expected.get(t) == s for t,s in members.items()), 'candidate member differs from seal')
    action = provider.get('action','apply'); need(action in {'apply','rollback'}, 'unknown action')
    # False means explicit preview only; missing/nonboolean never authorizes.
    need(type(dep.get('execution_enabled')) is bool, 'execution_enabled missing/not boolean')
    if dep['execution_enabled'] is False:
        return {'status':'PREVIEW_NOT_RESTORED','device_calls':0,'action':action,'plan_sha256':digest(package/'plan.json')}, 0
    need(not seal.get('synthetic') and not dep.get('synthetic'), 'synthetic documents cannot execute')
    need(plan.get('execution_enabled') is True, 'prepared plan disabled')
    auth_path = pin(provider['authorization'],base); auth = read(auth_path)
    need(auth.get('approved_by') == 'outer(codex)' and auth.get('serial') == args.serial and
         auth.get('plan_sha256') == digest(package/'plan.json'), 'independent authorization binding')
    need(auth.get('derived_manifest_sha256') == provider['prepared']['manifest_sha256'], 'derived release not outer pinned')
    need(type(auth.get('expires_epoch')) in {int,float} and auth['expires_epoch']>time.time(),'authorization expired')
    need(auth.get('actions')==['place-only','one-reboot','rollback-safe'],'authorization actions')
    need(BOOT.fullmatch(auth.get('boot_id','')),'authorization boot missing')
    if action=='apply':need(auth['boot_id']==plan['boot_id'],'authorization boot drift')
    need(isinstance(auth.get('holder'),str) and auth['holder'], 'holder not pinned')
    # Explicit held check; this adapter never acquires/releases another lane lock.
    lock_tool = pin(provider['lock_tool'],base)
    held = runner(['bash',str(lock_tool),'held',args.serial],capture_output=True,text=True,timeout=15)
    need(held.returncode == 0 and not held.stderr and held.stdout.strip() == auth['holder'], 'external holder drift')
    tx = resolve(provider['transaction_dir'],base) if action == 'rollback' else Path(args.out).resolve()
    cmd = [sys.executable,str(package/'executor.py'),'--plan',str(package/'plan.json'),'--execute',
           '--authorization',str(auth_path),'--authorization-sha256',provider['authorization']['sha256'],
           '--out',str(tx),'--action',action]
    # Real argv and returncode; no READY/visual success invented here.
    result = runner(cmd,capture_output=True,text=True,timeout=900)
    sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
    receipt = {'schema':'route-b-provider-receipt/v1','action':action,'serial':args.serial,
               'command':cmd,'executor_rc':result.returncode,'plan_sha256':digest(package/'plan.json'),
               'ui_accepted':False,'seal_signed':False}
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    write(str(args.out)+'.provider-receipt.json',receipt)
    return receipt, result.returncode


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seal'); p.add_argument('--serial'); p.add_argument('--deployment'); p.add_argument('--out')
    p.add_argument('--compile',action='store_true'); p.add_argument('--binding'); p.add_argument('--self-test',action='store_true')
    a = p.parse_args(argv)
    if a.self_test:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProviderTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        if a.compile:
            need(a.binding and a.out, '--compile requires binding/out')
            result=compile_package(a.binding,a.out); rc=0
        else:
            need(a.seal and a.serial and a.deployment and a.out,'standard argv incomplete')
            result,rc=invoke(a)
        print(json.dumps(result,ensure_ascii=False)); return rc
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as e:
        print('ROUTE-B PROVIDER REJECT: '+str(e),file=sys.stderr); return 2


class ProviderTests(unittest.TestCase):
    """Only the new adapter's local contract; no R1/device/VM/remote calls."""
    def test_hap_actual_source(self):
        p=Path.home()/'a2hlab-provision/ttbundle/source-host.hap'
        if not p.exists():self.skipTest('external HAP source absent')
        self.assertEqual(digest(p),HAP_SHA)

    def test_board_uid_not_inferred_from61b(self):
        b={'schema':'route-b-restore-binding/v1','serial':'5cd1e3dd00000000000000000923012c',
           'boot_id':'11111111-1111-1111-1111-111111111111','host_uid':20012345,
           'runtime_root':OLD_RT,'stage_root':OLD_STAGE,'socket':OLD_SOCKET,
           'attempt_root':OLD_ROOT+'-5cd'}
        board_binding(b)
        raw=(RELEASE/'payload/real-start-parent-bounded.sh').read_bytes()
        data=derive_text(raw,b)
        self.assertIn(b'20012345',data);self.assertNotIn(b'20011206',data)
        b['host_uid']=None
        with self.assertRaisesRegex(ValueError,'UID'):board_binding(b)

    def test_original_release_unchanged(self):
        self.assertEqual(digest(RELEASE/'executor.py'),EXECUTOR_SHA)
        self.assertEqual(digest(RELEASE/'payload/watchdog.sh'),'9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')

    def test_pin_real_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.write_bytes(b'actual')
            self.assertEqual(pin({'path':'file','sha256':digest(p)},tmp),p.resolve())
            with self.assertRaisesRegex(ValueError,'drift'):pin({'path':'file','sha256':'0'*64},tmp)

    def test_metadata_null_label_rejects(self):
        with self.assertRaisesRegex(ValueError,'label'):metadata({'mode':'550','uid':0,'gid':0,'label':None})

    def test_unknown_preimage_rejects(self):
        with self.assertRaisesRegex(ValueError,'proof'):before_image({'exists':False},'.')

    def test_derived_executor_compiles_keeps_transaction_guards(self):
        b={'serial':'5cd1e3dd00000000000000000923012c','attempt_root':OLD_ROOT+'-5cd'}
        code=new_executor((RELEASE/'executor.py').read_text(),b,{OLD_RT+'/fw/framework.jar'},
            [{'target':OLD_RT}])
        self.assertIn("SERIAL='5cd",code)
        for text in ('failed operation intent mismatch','preimage drift','after ',
                     'unknown guardian exit status','cfg-atomic-remount','expired'):
            self.assertIn(text,code)

    def test_standard_argv_actual_apply_and_rollback(self):
        """Actual compiled transaction via standard argv and a recording device.

        Input bytes are the real local221 archive; device metadata is an explicit
        isolated fixture, NOT today's 5cd measurements. No executable fixture
        directory survives. Test transport records writes, never invokes HDC.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();package=root/'package'
            serial='5cd1e3dd00000000000000000923012c'
            meta={'mode':'550','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
            uid=20011300;rtmeta=dict(meta,mode='440',uid=uid,gid=uid)
            rootmeta=dict(meta,mode='750')
            proof={'exists':False,'proof':'isolated fixture known absent'}
            b={'schema':'route-b-restore-binding/v1','serial':serial,
                'boot_id':'11111111-1111-1111-1111-111111111111','host_uid':uid,
                'runtime_root':OLD_RT,'stage_root':OLD_STAGE,'socket':OLD_SOCKET,
                'attempt_root':OLD_ROOT+'-5cd','startup_enabled':True,
                'release_inventory':{'path':str(RELEASE/'checkpoint-manifest.json'),'sha256':digest(RELEASE/'checkpoint-manifest.json')},
                'exe_alias_manifest':{'path':str(ALIASES/'manifest.json'),'sha256':digest(ALIASES/'manifest.json')},
                'runtime_archive':{'path':str(WS/'westlake-harness/benchmark/2026-10-12-toutiao-recovery-readonly/runtime-archive-2016/index.json')},
                'host_hap':{'path':str(Path.home()/'a2hlab-provision/ttbundle/source-host.hap'),'sha256':HAP_SHA},
                'before':{},'after':{},'storage':{
                    'runtime':{'exists':False,'proof':'isolated fixture absent RT','after':dict(rootmeta,uid=uid,gid=uid),'file_after':rtmeta},
                    'stage':{'exists':False,'proof':'isolated fixture absent stage','after':rootmeta}},
                'preserved':[{'target':OLD_STOP,'before':proof}],
                'required_directories':[], 'additional_directories':[], 'stage_files':[],
                'prerequisites':[{'target':'/data/app/el1/bundle/public/org.westlake.imehost/entry.hap','sha256':HAP_SHA}],
                'tools':copy.deepcopy(read(RELEASE/'plan.disabled.json')['tools'])}
            b['runtime_archive']['sha256']=digest(b['runtime_archive']['path'])
            b['directories']=[{'target':str(Path(b['attempt_root']).parent),'before':proof,'after':rootmeta},
                              {'target':b['attempt_root'],'before':proof,'after':rootmeta}]
            for d in ('/data/westlake-demo','/data/westlake-demo/toutiao','/data/westlake-demo/toutiao/scripts',
                      '/data/local/tmp/operator45','/data/local/tmp/operator45/selfheal48'):
                b['additional_directories'].append({'target':d,'before':proof,'after':rootmeta})
            for d in ('/data', '/data/local/tmp', '/system/etc/init',str(Path(OLD_RT).parent)):
                b['required_directories'].append({'target':d,'exists':True,'after':dict(rootmeta,uid=uid,gid=uid) if 'imehost' in d else rootmeta})
            oldplan=read(RELEASE/'plan.disabled.json')
            for m in oldplan['members']:
                t=m['target'].replace(OLD_ROOT,b['attempt_root']);b['before'][t]=proof;b['after'][t]=meta
            oldcfg=root/'old.cfg';oldcfg.write_bytes(b'old fixture cfg')
            b['before'][CFG]=dict(meta,exists=True,sha256=digest(oldcfg),source=str(oldcfg))
            for name in ('source_app_namespace','host_spawn','request.bin'):
                p=root/name;p.write_bytes((RELEASE/'payload/request-uid20011206.bin').read_bytes() if name=='request.bin' else b'ISOLATED NONEXECUTABLE TRANSPORT FIXTURE')
                b['stage_files'].append({'source':{'path':str(p),'sha256':digest(p)},'target':OLD_STAGE+'/'+name,'after':meta,'before':proof})
            bp=root/'binding.json';write(bp,b)
            result=compile_package(bp,package)
            self.assertEqual(result['device_calls'],0)
            plan=read(package/'plan.json')
            self.assertEqual(plan['serial'],serial)
            self.assertEqual(struct.unpack_from('<I',(package/'runtime/stage/request.bin').read_bytes(),312)[0],uid)
            self.assertIn('AUTH_UID=20011300',(package/'payload/config-common.sh').read_text())
            self.assertIn('appspawn-x',(package/'payload/launch-common.sh').read_text())
            entry=(package/'payload/entry.sh').read_text()
            self.assertIn(digest(package/'payload/watchdog.sh'),entry)
            self.assertIn(digest(package/'payload/route-b-owner.sh'),entry)
            calls=[]
            model=RecordingDevice(plan)
            def recording_runner(command,**kw):
                calls.append(command)
                if command[0]=='bash':return subprocess.CompletedProcess(command,0,'fixture-holder\n','')
                spec=importlib.util.spec_from_file_location('isolated_new_executor',package/'executor.py')
                mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
                mod.Device=lambda p,out:model
                stdout,stderr=io.StringIO(),io.StringIO()
                with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                    rc=mod.main(command[2:])
                return subprocess.CompletedProcess(command,rc,stdout.getvalue(),stderr.getvalue())
            lock=root/'lock.sh';lock.write_text('# fixture only\n')
            authpath=root/'auth.json'
            auth={'approved_by':'outer(codex)','serial':serial,'boot_id':plan['boot_id'],
                'expires_epoch':time.time()+300,'plan_sha256':digest(package/'plan.json'),
                'derived_manifest_sha256':digest(package/'manifest.json'),'holder':'fixture-holder',
                'actions':['place-only','one-reboot','rollback-safe']}
            write(authpath,auth)
            prov={'layer':'toutiao-route-b','program':{'path':str(Path(__file__).resolve()),'sha256':digest(__file__)},
                'targets':[r['target'] for r in plan['members']],
                'prepared':{'path':str(package),'manifest_sha256':digest(package/'manifest.json')},
                'authorization':{'path':str(authpath),'sha256':digest(authpath)},
                'lock_tool':{'path':str(lock),'sha256':digest(lock)},'action':'apply'}
            dep={'schema':'demo-restore-deployment/v1','execution_enabled':False,'providers':[prov]}
            seal={'schema':'demo-seal/v1','files':{'overlays':{r['target']:r['sha256'] for r in plan['members']}}}
            dp=root/'deployment.json';sp=root/'seal.json';write(dp,dep);write(sp,seal)
            args=argparse.Namespace(seal=str(sp),serial=serial,deployment=str(dp),out=str(root/'tx'))
            preview,rc=invoke(args,recording_runner);self.assertEqual(rc,0);self.assertEqual(calls,[])
            dep['execution_enabled']=True;dp.write_text(json.dumps(dep))
            receipt,rc=invoke(args,recording_runner)
            self.assertEqual(rc,0);self.assertTrue((root/'tx/placed.json').exists())
            self.assertGreater(len(model.sends),240)
            self.assertNotIn('--authorize-execute',calls[-1]);self.assertIn('--execute',calls[-1])
            prov['action']='rollback';prov['transaction_dir']=str(root/'tx');dp.write_text(json.dumps(dep))
            args.out=str(root/'rollback-call')
            receipt,rc=invoke(args,recording_runner);self.assertEqual(rc,0)
            self.assertTrue((root/'tx/rollback.json').exists())
            self.assertEqual(model.files[CFG]['sha256'],digest(package/'payload/rollback-inert.cfg'))
            for row in plan['members']:
                if row['target']!=CFG:self.assertFalse(model.probe(row['target'])['exists'])
            # A changed prepared member rejects before the held/transport runner.
            calls.clear();(package/'payload/entry.sh').write_bytes(b'DRIFT')
            with self.assertRaisesRegex(ValueError,'drift'):invoke(args,recording_runner)
            self.assertEqual(calls,[])


class RecordingDevice:
    """Directory-aware file model ONLY used by --self-test. No HDC/shell exec."""
    def __init__(self,plan):
        self.plan=plan;self.files={};self.dirs={d['target']:d['after'] for d in plan['directory_prerequisites']};self.sends=[]
        self.rows={r['target']:r for r in plan['members']}
        for r in plan['members']+plan['preserved']:
            if r['before']['exists']:self.files[r['target']]=copy.deepcopy(r['before'])
        for r in plan['prerequisites']:self.files[r['target']]={'exists':True,'sha256':r['sha256']}
    def probe(self,t):return copy.deepcopy(self.files.get(t,{'exists':False}))
    def recv(self,name,target,dest):shutil.copyfile(self.files[target]['source'],dest)
    def send(self,name,source,target):
        self.sends.append((name,str(source),target))
        meta=self.rows.get(target,{}).get('after',{'mode':'550','uid':0,'gid':0,'label':'u:object_r:data_file:s0'})
        self.files[target]=dict(meta,exists=True,sha256=digest(source),source=str(source))
    def shell(self,name,script):
        if name=='boot':return self.plan['boot_id']
        if name=='directory-absence':
            target=re.search(r'test ! -e ([^ ;]+)',script)[1]
            if target in self.dirs:raise ValueError('directory exists')
            return ''
        if name in {'existing-host-directory','directory-readback'}:
            row=next(d for d in self.plan['directories']+self.plan['directory_prerequisites'] if 'test -d '+d['target']+';' in script)
            m=self.dirs[row['target']];return m['mode']+':'+str(m['uid'])+':'+str(m['gid'])+'\n'+m['label']+' dir'
        if name=='directory-create':
            row=next(d for d in self.plan['directories'] if 'mkdir '+d['target']+';' in script)
            self.dirs[row['target']]=row['after'];return ''
        if name=='parent-directory-read':return ''
        if name=='control-metadata':return ''
        if name=='cfg-atomic-remount':
            src=next(v for k,v in self.files.items() if k.startswith(self.plan['directories'][0]['target'].rsplit('/',1)[0]+'/') and '/cfg-stage-' in k and k in script)
            self.files[CFG]=dict(self.rows[CFG]['after'],exists=True,sha256=src['sha256'],source=src['source']);return ''
        if name=='rollback-stop-create':return ''
        if name=='remove-own-addition':
            target=script.rsplit('rm ',1)[1].strip("'");self.files.pop(target,None);return ''
        if name=='remove-empty-owned-storage-directory':return ''
        raise ValueError('unhandled recording-device operation '+name)


if __name__ == '__main__':
    sys.exit(main())
