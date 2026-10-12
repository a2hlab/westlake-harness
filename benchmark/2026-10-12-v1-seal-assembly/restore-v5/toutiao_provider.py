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

Binding schema route-b-restore-binding/v2:
  serial, boot_id, host_uid, runtime_root, stage_root, socket, attempt_root;
  release_inventory{path,sha256}, runtime_archive{path,sha256}, host_hap{path,sha256};
  before{target:exact metadata/absence proof}, after{target:mode/uid/gid/label};
  directories (new candidate root only), preserved (old stop only), tools;
  runtime_file_metadata{target:{after,metadata_evidence}},
  extra_runtime_files/stage_files[{source pin,target,after,before,metadata_evidence}],
  new_storage_directories[{target,after,before,metadata_basis}], required_directories;
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
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[3])))
RELEASE = WS / 'westlake-harness/benchmark/2026-10-12-recovery-executor'
ALIASES = WS / 'westlake-harness/benchmark/2026-10-12-recovery-exe-alias'
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
         and '..' not in value.split('/') and str(Path(value)) == value, 'unsafe board path')
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
    need(b.get('schema') == 'route-b-restore-binding/v2', 'wrong binding schema')
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


def observed_metadata(row, source_sha, target, b, base):
    """A current readback pin, never a tar header, is metadata authority.

    evidence.target selects exactly one row of a pinned board index. The only
    ownership projection is captured donor host UID/GID -> installed host UID.
    Mode and SELinux label are preserved byte-for-byte. Final after is explicit.
    """
    evidence = row.get('metadata_evidence', {})
    path = pin(evidence, base)
    index = read(path)
    observed_target = evidence.get('target')
    if isinstance(index.get('files'), dict):
        # Metadata-only capture has no SHA claim. Bind its raw numbered transport
        # and stdout separately from the archive/CAS byte pin.
        transport = read(pin(evidence.get('transport'), base))
        output = pin(evidence.get('stdout'), base)
        argv = transport.get('argv', [])
        need(len(argv) >= 5 and argv[1] == '-t' and argv[3] == 'shell'
             and transport.get('exit') == 0 and transport.get('stdout_sha256') == digest(output),
             'metadata transport evidence')
        observation_serial = argv[2]
        need(index.get('stable') is True, 'metadata capture unstable')
        observed = index['files'].get(observed_target)
        need(isinstance(observed, dict), 'metadata evidence target missing')
        raw = output.read_text().replace('\r', '')
        lines = raw.splitlines()
        need(lines[-1:] == ['RE_REMOTE_RC=0'], 'metadata remote status')
        marker = 'PATH='+str(observed_target)
        need(lines.count(marker) == 1, 'metadata raw target missing/duplicate')
        pos = lines.index(marker)
        need(lines[pos+1] == ':'.join(str(observed[k]) for k in ('mode','uid','gid'))
             and observed['label'] in lines[pos+2].split(), 'metadata index/raw mismatch')
    else:
        observation_serial = index.get('serial')
        need(index.get('stable_boot') is True, 'metadata capture unstable')
        observed = [r for r in index.get('files', []) if r.get('target') == observed_target]
        need(len(observed) == 1, 'metadata evidence target missing/duplicate')
        observed = observed[0]
        need(observed.get('observed') is True and observed.get('sha256') == source_sha,
             'metadata observation SHA/regular-file proof')
    need(observation_serial in SERIALS and BOOT.fullmatch(index.get('boot_id', '')),
         'metadata observation identity')
    need(observed_target == target or observed_target.replace(OLD_RT+'/', b['runtime_root']+'/', 1) == target
         or observed_target.replace(OLD_STAGE+'/', b['stage_root']+'/', 1) == target,
         'metadata evidence wrong target')
    metadata(observed)
    expected = {k: observed[k] for k in ('mode', 'uid', 'gid', 'label')}
    if observation_serial == OLD_SERIAL:
        for key in ('uid', 'gid'):
            if expected[key] == OLD_UID: expected[key] = b['host_uid']
    metadata(row.get('after'))
    need(row['after'] == expected, 'per-file metadata projection differs from observation: '+target)
    return expected


def storage_directories(b, targets):
    """Every new directory is declared, including empty namespace mount targets.

    No recursive user-data copy or deletion. Metadata is explicit per directory;
    metadata_basis describes the captured evidence or reviewed creation policy.
    """
    required = set()
    for root, kind in ((b['runtime_root'], 'runtime'), (b['stage_root'], 'stage')):
        state = b['storage'][kind]
        need(state.get('exists') is False and state.get('proof'), 'absent '+kind+' root proof required')
        required.add(root)
        for t in targets:
            if not ancestor_of(root, t): continue
            parent = str(Path(t).parent)
            while parent != root:
                required.add(parent); parent = str(Path(parent).parent)
    required.update(b['runtime_root']+'/'+n for n in ('private-tmp', 'private-tmp/asx', 'app-data', 'i18n/etc/icu', 'data', 'tzdata'))
    out = copy.deepcopy(b.get('new_storage_directories', []))
    names = set()
    allowed = {'/data/westlake-demo', '/data/westlake-demo/toutiao',
        '/data/westlake-demo/toutiao/scripts', '/data/local/tmp/operator45',
        '/data/local/tmp/operator45/selfheal48'}
    for d in out:
        t = safe_path(d.get('target'))
        need(t not in names, 'duplicate storage directory'); names.add(t)
        need(t in allowed or any(t == r or ancestor_of(r, t) for r in (b['runtime_root'], b['stage_root'])),
             'unapproved new storage directory')
        need(d.get('before', {}).get('exists') is False and d['before'].get('proof'), 'directory absence missing')
        metadata(d.get('after'))
        need(isinstance(d.get('metadata_basis'), str) and d['metadata_basis'].strip(), 'directory metadata basis missing')
    need(required <= names, 'undeclared storage/namespace directories: '+str(sorted(required-names)))
    for suffix in ('', 'private-tmp', 'app-data', 'i18n/etc/icu'):
        target = b['runtime_root']+('/'+suffix if suffix else '')
        d = next(d for d in out if d['target'] == target)
        need(d['after']['uid'] == b['host_uid'], 'namespace directory host UID mismatch')
    return sorted(out, key=lambda d:(d['target'].count('/'), d['target']))



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
    # A file transaction journal alone cannot establish ownership of directories.
    # Journal each directory intent, and publish ownership only AFTER readback.
    old="    for directory in plan.get('directories',[]):\n        meta=directory['after'];target=directory['target'];check_identity(dev,plan)"
    new="    for directory_number,directory in enumerate(plan.get('directories',[])):\n        meta=directory['after'];target=directory['target'];check_identity(dev,plan)\n        save(out/('directory-intent-%03d.json'%directory_number), {'plan_sha256':plan['_sha'],'target':target,'after':meta})"
    need(changed.count(old)==1,'directory journal anchor drift')
    changed=changed.replace(old,new,1)
    anchor="        require(got.splitlines()[0]==meta['mode']+':'+str(meta['uid'])+':'+str(meta['gid']) and meta['label'] in got.splitlines()[1].split(),'directory metadata readback')"
    need(changed.count(anchor)==1,'directory ownership anchor drift')
    changed=changed.replace(anchor,anchor+"\n        save(out/('directory-created-%03d.json'%directory_number), {'plan_sha256':plan['_sha'],'target':target,'after':meta})",1)
    old="        got=dev.shell('directory-readback','set -eu; test -d '+q(target)+'; test ! -L '+q(target)+\"; stat -c '%a:%u:%g' \"+q(target)+'; ls -ldnZ '+q(target))"
    new=old[:-1]+"+\"; stat -c '%d:%i' \"+q(target))"
    need(changed.count(old)==1,'directory identity readback anchor drift')
    changed=changed.replace(old,new,1)
    old="        save(out/('directory-created-%03d.json'%directory_number), {'plan_sha256':plan['_sha'],'target':target,'after':meta})"
    new="        require(len(got.splitlines())==3 and re.fullmatch(r'[0-9]+:[0-9]+',got.splitlines()[2]),'directory identity missing')\n        save(out/('directory-created-%03d.json'%directory_number), {'plan_sha256':plan['_sha'],'target':target,'after':meta,'identity':got.splitlines()[2]})"
    need(changed.count(old)==1,'directory identity journal anchor drift')
    changed=changed.replace(old,new,1)
    # An absent original CFG has no metadata and no unsafe donor to quarantine.
    # Restore its actual absence with a guarded remount trap, not guessed fields.
    anchor="        if row['target']==CFG:\n            # Always quarantine"
    need(changed.count(anchor)==1,'absent CFG rollback anchor drift')
    changed=changed.replace(anchor,"""        if row['target']==CFG and not before['exists']:
            if observed['exists']:
                remove_added_cfg(dev,observed['sha256'])
                require(not dev.probe(CFG)['exists'],'new CFG removal readback')
            continue
        if row['target']==CFG:
            # Always quarantine""",1)
    helper=r'''def remove_added_cfg(dev,expected_sha):
    script=("set -eu; reseal=0; trap 'rc=$?; if [ \"$reseal\" = 1 ]; then mount -o ro,remount / || rc=1; fi; exit \"$rc\"' EXIT; "
            "opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4); "
            "case ,$opts, in *,rw,*) ;; *,ro,*) mount -o rw,remount /; reseal=1;; *) exit 2;; esac; "
            'test ! -L '+q(CFG)+'; test -f '+q(CFG)+'; '
            'test "$(sha256sum '+q(CFG)+' | cut -d\' \' -f1)" = '+q(expected_sha)+'; '
            'rm '+q(CFG))
    dev.shell('cfg-remove-added-remount',script)

'''
    changed=changed.replace('def rollback(plan,dev,out):',helper+'def rollback(plan,dev,out):',1)
    # Receipt publication is AFTER guarded cleanup; failed attempts are immutable
    # separate receipts. Re-running rollback rechecks every backup/member first.
    anchor="    # Evidence/stop directories are intentionally retained, never rmtree."
    start=changed.index(anchor); end=changed.index('\ndef main(',start)
    cleanup = r"""
def cleanup_storage(plan,dev,out,all_directories=False):
    failures=[]
    candidates=plan.get('directories' if all_directories else 'storage_directories',[])
    pending=list(reversed(candidates))
    for position,d in enumerate(pending):
        path=d['target']; m=d['after']
        try:
            check_identity(dev,plan)
            number=next(i for i,row in enumerate(plan['directories']) if row['target']==path)
            ownership=out/('directory-created-%03d.json'%number)
            if not ownership.exists():
                # Unknown creation or failed metadata/readback is not ownership.
                # Even an empty same-metadata directory must be retained.
                dev.shell('unknown-directory-must-be-absent',
                          'set -eu; test ! -e '+q(path)+'; test ! -L '+q(path))
                continue
            owned=read(ownership)
            require({k:owned.get(k) for k in ('plan_sha256','target','after')}=={'plan_sha256':plan['_sha'],'target':path,'after':m}
                    and re.fullmatch(r'[0-9]+:[0-9]+',owned.get('identity','')), 'directory ownership journal drift')
            dev.shell('remove-empty-owned-storage-directory',
                'set -eu; test ! -L '+q(path)+'; if [ -e '+q(path)+' ]; then test -d '+q(path)+
                "; test \"$(stat -c '%a:%u:%g' "+q(path)+")\" = "+q(m['mode']+':'+str(m['uid'])+':'+str(m['gid']))+
                '; ls -ldnZ '+q(path)+' | grep -F '+q(m['label'])+' >/dev/null; '+
                "test \"$(stat -c '%d:%i' "+q(path)+")\" = "+q(owned['identity'])+'; rmdir '+q(path)+'; fi')
        except (OSError,ValueError,KeyError,TypeError) as error:
            failures.append({'target':path,'error':str(error)})
            # Identity/transport ambiguity is not permission to keep mutating.
            break
    if failures:
        number=0
        while (out/('rollback-cleanup-failed-%03d.json'%number)).exists():number+=1
        save(out/('rollback-cleanup-failed-%03d.json'%number),
             {'state':'CONTROLS_RESTORED_STORAGE_CLEANUP_FAILED','plan_sha256':plan['_sha'],
              'residual_or_unverified':failures,'remaining_unverified':[d['target'] for d in pending[position:]],
              'retryable':True,'success':False,
              'app_signals':0,'user_data_deleted':False})
        raise ValueError('storage cleanup incomplete; residual retained; retry rollback with same transaction')

"""
    changed=changed[:start]+"""    # Candidate evidence/stop directories remain intentionally quarantined.
    cleanup_storage(plan,dev,out)
    receipt=out/'rollback.json'
    if not receipt.exists():save(receipt,{'state':('ROLLED_BACK_CONTROLS_CFG_ABSENCE_RESTORED' if any(r['target']==CFG and not r['before']['exists'] for r in plan['members']) else 'ROLLED_BACK_CONTROLS_BOOT_TRIGGER_QUARANTINED'),'storage_cleanup_complete':True,'retained_evidence_directories':plan.get('retained_directories',[]),'unsafe_donor_restarted':False,'app_signals':0})
"""+cleanup+changed[end:]
    anchor="    if all(equal(current[r['target']],r['before']) for r in tx['backups']):\n"
    need(changed.count(anchor)==1,'no-change cleanup anchor drift')
    changed=changed.replace(anchor,anchor+"        cleanup_storage(plan,dev,out,all_directories=not any(out.glob('intent-*.json')))\n",1)
    changed=changed.replace("'state':'NO_MEMBER_CHANGES_NO_DONOR_RESTART','app_signals':0", "'state':'NO_MEMBER_CHANGES_NO_DONOR_RESTART','directory_cleanup_complete':True,'app_signals':0",1)
    compile(changed,'derived-executor.py','exec')
    return changed


def control_bundle(b, base):
    """Read exactly the measured24-control readiness release, never its authority.

    Inputs are independently pinned: actual plan, composition, base23 plan and
    donor worker observation. The target's own before images still come from b.
    """
    refs = b['control_source']
    plan_path = pin(refs['plan'], base)
    composition_path = pin(refs['composition'], base)
    root = composition_path.parent
    need(plan_path.parent == root, 'control plan outside package')
    composition = read(composition_path)
    base_plan_path = pin(refs['base_plan'], base)
    worker_path = pin(refs['worker_preimage'], base)
    need(composition.get('schema') == 'child-readiness-composition/v1'
         and composition['base_plan_sha256'] == digest(base_plan_path)
         and composition['preimage_sha256'] == digest(worker_path), 'control source lineage drift')
    listed = set()
    for row in composition['files']:
        name = row['path']
        need(not Path(name).is_absolute() and '..' not in Path(name).parts and name not in listed, 'control inventory path')
        listed.add(name)
        src = root/name
        need(src.is_file() and not src.is_symlink() and digest(src) == row['sha256']
             and src.stat().st_size == row['bytes'], 'control inventory drift: '+name)
    plan = read(plan_path); baseline = read(base_plan_path)
    worker_target = OLD_ROOT+'/readiness-probe.sh'
    expected = {r['target'] for r in read(RELEASE/'plan.disabled.json')['members']} | {worker_target}
    need(len(plan['members']) == 24 and {r['target'] for r in plan['members']} == expected, 'control24 target set drift')
    need(len(baseline['members']) == 23 and {r['target'] for r in baseline['members']} == expected-{worker_target}, 'control base23 target set drift')
    worker = read(worker_path)
    need(worker['target'] == worker_target and worker['exists'] is False and worker.get('proof'), 'donor worker lineage missing')
    names = set()
    for row in plan['members']:
        source = row['source']
        need(source.startswith('$PACKAGE/payload/') and len(Path(source).parts) == 3, 'control member source path')
        relative = source.removeprefix('$PACKAGE/')
        need(relative in listed and digest(root/relative) == row['sha256'], 'control plan/payload SHA drift')
        metadata(row['after']); names.add(Path(source).name)
    need('readiness-probe.sh' in names and digest(root/'executor.py') == EXECUTOR_SHA, 'readiness worker/executor missing')
    # Scope lineage comes from base but no supplied executable authority is copied.
    need(plan['serial'] == OLD_SERIAL and plan['scope'] == baseline['scope'], 'control donor scope/serial')
    return plan, root/'payload', names


def guardian_update(b, base, control_root):
    """Pinned r2b/r3 guardian delta; target observations stay in the 5cd binding."""
    ref = b.get('guardian_update')
    if ref is None: return {}
    manifest_path = pin(ref, base); root = manifest_path.parent
    manifest = read(manifest_path)
    schema = manifest.get('schema')
    need(schema in {'quiet-reset-checkpoint/v1','lowfork-audit-checkpoint/v1'}, 'guardian update schema')
    listed = set()
    for row in manifest['files']:
        name = row['path']
        need(not Path(name).is_absolute() and '..' not in Path(name).parts and name not in listed, 'guardian inventory path')
        listed.add(name); source = root/name
        need(source.is_file() and not source.is_symlink() and digest(source)==row['sha256']
             and source.stat().st_size==row['bytes'], 'guardian update bytes drift: '+name)
    need({'candidate/route-b-owner.sh','candidate/watchdog.sh','candidate/readiness-probe.sh','candidate/launch-common.sh'} <= listed,
         'guardian update core missing')
    updated = {'route-b-owner.sh'}
    if schema == 'lowfork-audit-checkpoint/v1': updated.add('readiness-probe.sh')
    for name in {'watchdog.sh','readiness-probe.sh','launch-common.sh'} - updated:
        need(digest(root/'candidate'/name)==digest(control_root/name), 'guardian update exceeded declared delta: '+name)
    return {name: root/'candidate'/name for name in updated}


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
    oldplan, control_root, control_names = control_bundle(b, base)
    updated_guardian = guardian_update(b, base, control_root)
    # All input metadata/local bytes checked before creating package.
    rows = []
    seen = set()
    for a in index['files']:
        old = safe_path(a['target'])
        need(old.startswith(OLD_RT + '/'), 'foreign archive target')
        suffix = old[len(OLD_RT) + 1:]
        need(suffix.split('/')[0] != 'stage', 'reserved local stage namespace')
        need(not set(suffix.split('/')) & {'app-data', 'data', 'webview', 'cache'}, 'user-state archive member')
        target = b['runtime_root'] + '/' + suffix
        need(target not in seen, 'duplicate archive target')
        seen.add(target)
        source = pin({'path': a['source'], 'sha256': a['sha256']}, base)
        row = b.get('runtime_file_metadata', {}).get(target)
        need(isinstance(row, dict), 'per-file runtime metadata missing: '+target)
        meta=observed_metadata(row, a['sha256'], target, b, base)
        before={'exists':False,'proof':b['storage']['runtime']['proof']}
        metadata(meta); before_image(before, base)
        rows.append((target, suffix, source, meta, before))
    closure = read(pin(b['runtime_closure'], base))
    need(closure.get('serial') in SERIALS and closure.get('stable_boot') is True
         and not closure.get('missing_or_nonregular'), 'runtime closure capture incomplete')
    closure_targets = [r['target'].replace(OLD_RT+'/', b['runtime_root']+'/', 1) for r in closure['files']]
    need(len(closure_targets) == len(set(closure_targets)), 'duplicate closure observation')
    need(set(closure_targets) == {r['target'] for r in b.get('extra_runtime_files', [])},
         'extra runtime differs from captured closure set')
    for extra in b.get('extra_runtime_files', []):
        target = safe_path(extra.get('target'))
        need(ancestor_of(b['runtime_root'], target), 'extra runtime outside root')
        need(target not in seen, 'extra runtime overlaps archive/extra target: '+target)
        suffix = target[len(b['runtime_root'])+1:]
        need(suffix.split('/')[0] != 'stage', 'reserved local stage namespace')
        need(not set(suffix.split('/')) & {'app-data', 'data', 'webview', 'webview-t-data', 'cache', 'private-tmp'}, 'user-state extra runtime')
        current = next(r for r in closure['files'] if r['target'].replace(OLD_RT+'/',b['runtime_root']+'/',1) == target)
        need(extra['source']['sha256'] == current['sha256'], 'extra differs from current closure SHA')
        need(pin(extra['metadata_evidence'], base) == pin(b['runtime_closure'], base), 'extra metadata not current closure')
        source = pin(extra['source'], base)
        meta = observed_metadata(extra, extra['source']['sha256'], target, b, base)
        before_image(extra['before'], base)
        need(extra['before']['exists'] is False, 'absent runtime root conflicts with file preimage')
        seen.add(target); rows.append((target, suffix, source, meta, extra['before']))
    mandatory = {'appspawn-x', 'boot/boot.art', 'etc/fonts.xml', 'i18n/etc/icu/icudt75l.dat'}
    need({b['runtime_root']+'/'+n for n in mandatory} <= seen, 'runtime consumed dependency missing')
    # Font references are data, not a hard-coded font-count completeness claim.
    import xml.etree.ElementTree as ET
    fonts_source = next(row[2] for row in rows if row[0] == b['runtime_root']+'/etc/fonts.xml')
    for font in ET.fromstring(fonts_source.read_bytes()).iter('font'):
        name = (font.text or '').strip()
        need(name and '/' not in name and name not in {'.', '..'}, 'unsafe font reference')
        need(b['runtime_root']+'/fonts/'+name in seen, 'referenced font missing: '+name)
    for s in b.get('stage_files', []):
        target = safe_path(s['target'])
        need(target.startswith(b['stage_root'] + '/') and target not in seen, 'stage target outside route')
        need(not set(target[len(b['stage_root'])+1:].split('/')) & {'app-data', 'data', 'webview', 'cache'}, 'user stage path')
        metadata(s['after']); before_image(s['before'], base)
        source = pin(s['source'], base)
        observed_metadata(s, s['source']['sha256'], target, b, base)
        seen.add(target); rows.append((target, 'stage/' + target[len(b['stage_root'])+1:], source, s['after'], s['before']))
    need({s['target'] for s in b.get('stage_files', [])} >=
         {b['stage_root']+'/'+n for n in ('source_app_namespace', 'host_spawn', 'request.bin')}, 'actual stage tools/request missing')
    preserved = b.get('preserved')
    need(isinstance(preserved, list) and len(preserved) == 1 and preserved[0]['target'] == OLD_STOP,
         'historical stop binding required')
    before_image(preserved[0]['before'], base)
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
    for name in sorted(control_names):
        p = updated_guardian.get(name, control_root/name)
        raw = p.read_bytes()
        data = derive_text(raw, b) if p.suffix in {'.sh', '.cfg', '.env'} else raw
        (out / 'payload' / p.name).write_bytes(data)
        if data != raw:
            changes.append({'path': 'payload/' + p.name, 'before_sha256': digest(p),
                            'after_sha256': hashlib.sha256(data).hexdigest(),
                            'diff': ''.join(difflib.unified_diff(raw.decode().splitlines(True), data.decode().splitlines(True)))})
    plan = copy.deepcopy(oldplan)
    plan.update(serial=b['serial'], boot_id=b['boot_id'], execution_enabled=b.get('startup_enabled', False),
                preserved=copy.deepcopy(preserved), tools=b['tools'], prerequisites=b['prerequisites'],
                directories=sorted(all_dirs,key=lambda d:(d['target'].count('/'),d['target'])), storage_directories=[d for d in storage if any(d['target']==r or ancestor_of(r,d['target']) for r in (b['runtime_root'],b['stage_root']))],
                retained_directories=[d['target'] for d in all_dirs if not any(d['target']==r or ancestor_of(r,d['target']) for r in (b['runtime_root'],b['stage_root']))],
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
    # Derived per-board executor: guarded typed storage and receipt sequencing.
    code = (RELEASE / 'executor.py').read_text()
    changed = new_executor(code,b,seen,all_dirs)
    (out / 'executor.py').write_text(changed)
    changes.append({'path': 'executor.py', 'before_sha256': EXECUTOR_SHA, 'after_sha256': digest(out / 'executor.py'),
                    'diff': ''.join(difflib.unified_diff(code.splitlines(True), changed.splitlines(True)))})
    # The independently accepted alias entry pins the actual derived watchdog/helper.
    entry=out/'payload/entry.sh';entry_text=entry.read_text()
    for name in ('watchdog.sh','route-b-owner.sh'):
        oldpin=digest(control_root/name);need(entry_text.count(oldpin)==1,'entry pin drift: '+name)
        entry_text=entry_text.replace(oldpin,digest(out/'payload'/name))
    entry.write_text(entry_text)
    # Build the per-boot file manifest from actual NEW bytes, never stale originals.
    manifest_rows = []
    for line in (control_root/'members.tsv').read_text().splitlines():
        _, name, mode = line.split(); p = out / 'payload' / {'start-parent.sh':'start-parent-prepared.sh', 'spawn.sh':'spawn-prepared.sh', 'screen-gate':'screen-gate-feed'}.get(name, name)
        manifest_rows.append(digest(p) + ' ' + name + ' ' + mode)
    (out / 'payload/members.tsv').write_text('\n'.join(manifest_rows) + '\n')
    config = (out / 'payload/startup.env').read_text()
    fields = {'STARTUP_APPROVED_BY': 'outer(codex)' if b.get('startup_enabled', False) else 'PENDING',
              'STARTUP_ENABLED': '1' if b.get('startup_enabled', False) else '0',
              'STARTUP_MEMBERS_SHA': digest(out / 'payload/members.tsv'),
              'STARTUP_START_PARENT_SHA': digest(out / 'payload/real-start-parent-bounded.sh')}
    by_target = {m['target']: m['sha256'] for m in plan['members']}
    for key, name in [('STARTUP_JIT_SHA','prepare_jit50.sh'), ('STARTUP_REQUEST_SHA','request.bin'),
                      ('STARTUP_NAMESPACE_SHA','source_app_namespace'),('STARTUP_HOST_SPAWN_SHA','host_spawn')]:fields[key]=by_target[(b['runtime_root'] if name=='prepare_jit50.sh' else b['stage_root'])+'/'+name]
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
    write(out / 'derivation.json', {'source_executor_sha256': EXECUTOR_SHA, 'control_source': b['control_source'], 'guardian_update': b.get('guardian_update'), 'changes': changes,
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
        plan['directories'])
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
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ProviderTests),
            unittest.defaultTestLoader.discover(str(HERE), pattern='test_restore_v5.py')])
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
        b={'schema':'route-b-restore-binding/v2','serial':'5cd1e3dd00000000000000000923012c',
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
