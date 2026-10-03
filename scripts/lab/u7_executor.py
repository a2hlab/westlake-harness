#!/usr/bin/env python3
"""One stopped-parent native + boot + JAR transaction. Dry-run never creates a Board.

File overlays leave every baseline directory/JAR layer in place. No installer,
remount-rw, parent kill, runtime hash-policy bypass, or implicit unlock.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time
import uuid

import deploy_generation as native
import deployment_native_gate as native_gate
import generation_bundle as bundle
import lab_paths
from sweep_bind_deploy import stage_file, bind_file, unbind_file, short_fingerprint

HOST = '/system/bin/appspawn-x'
EMPTY = hashlib.sha256(b'').hexdigest()
PROVENANCE_REGISTRY = Path(__file__).resolve().parents[2]/'knowledge/gates/image-provenance-exceptions.json'


def approved_provenance(receipt, registry=PROVENANCE_REGISTRY):
    """Exact, approved retrospective equivalence; never invent a historical receipt."""
    if receipt.get('status') != 'verified-with-exception':
        return False
    entries = json.loads(Path(registry).read_text())['exceptions']
    matches = [e for e in entries if e['id'] == receipt.get('exception_id') and e['status'] == 'approved']
    if len(matches) != 1:
        raise ValueError('image provenance exception missing or unapproved')
    entry = matches[0]
    for key in ['input_jars', 'outputs', 'build_command', 'dex2oat_sha256', 'frozen_tools', 'evidence']:
        if receipt.get(key) != entry[key]:
            raise ValueError('image provenance exception binding mismatch: ' + key)
    repo = Path(__file__).resolve().parents[2]
    for name, digest in entry['evidence'].items():
        path = (repo/name).resolve()
        if not path.is_relative_to(repo) or bundle.sha(path) != digest:
            raise ValueError('image provenance evidence drift: ' + name)
    return True


def effective_files(manifest, prefix=''):
    """Expand native directory mounts, with longest-target alias precedence."""
    rows = {}
    for mount in sorted(manifest['mounts'], key=lambda r: len(r['target'])):
        src, dst = mount['source'], mount['target']
        for target in list(rows):
            if target == dst or target.startswith(dst + '/'):
                del rows[target]
        for name, digest in manifest['files'].items():
            if name == src or name.startswith(src + '/'):
                target = dst + name[len(src):]
                rows[target] = {'source': prefix + name, 'target': target, 'sha256': digest}
    for target, digest in manifest['live_hashes'].items():
        if target not in rows or rows[target]['sha256'] != digest:
            raise ValueError('native alias does not resolve to sealed bytes: ' + target)
    return rows


def receipt_check(root, data, manifest):
    entry = data.get('paired_build_receipt')
    if not entry:
        return {'status': 'unknown', 'reason': 'no paired image build receipt'}
    receipt = json.loads(bundle.member(root, entry).read_text())
    # Explicit overlays (including both T8 JARs) supersede native underlays.
    overlays = {r['target']: r for r in data['boot_group']['members']}
    inputs = {j + '.jar': overlays[bundle.FW+j+'.jar']['sha256']
              if bundle.FW+j+'.jar' in overlays else bundle.sha(root / data['native']['directory'] /
              'payload/android/framework' / (j + '.jar')) for j in bundle.JARS}
    if manifest.get('mounts'):
        inputs = {j+'.jar': bundle.sha(p) for j,p in bundle.bcp_members(root,data,manifest).items()}
    outputs = {Path(r['target']).name: r['sha256'] for r in data['boot_group']['members']
               if r['target'] in bundle.IMAGE_TARGETS}
    for key, expected in [('input_jars', inputs), ('outputs', outputs)]:
        if receipt.get(key) != expected:
            raise ValueError('paired image receipt mismatch: ' + key)
    # A retrospective inventory is useful evidence, not an invented build-time receipt.
    complete = (receipt.get('status') == 'verified' and receipt.get('build_command') and
                all(re.fullmatch('[0-9a-f]{64}', str(receipt.get(k, '')))
                    for k in ['dex2oat_sha256', 'toolchain_identity_sha256', 'build_log_sha256']))
    status = 'verified-with-exception' if approved_provenance(receipt) else ('verified' if complete else 'unknown')
    return {'status': status, 'receipt': receipt,
            'sha256': entry['sha256']}


def prepare(root, baseline_native):
    root = Path(root).resolve(); baseline_native = Path(baseline_native).resolve()
    data, manifest, expected = bundle.validate(root)
    old = native.load_package(baseline_native)
    native.validate_upgrade(old, manifest)
    rows = effective_files(manifest, data['native']['directory'] + '/')
    baseline = {p: r['sha256'] for p, r in effective_files(old).items()}
    # References describe actual resident JAR/image overlays, overriding package underlays.
    refs = {k: bundle.read_fingerprint(bundle.member(root, data['reference'][k]))
            for k in ['runtime', 'boot']}
    for values in refs.values(): baseline.update(values)
    baseline.update(old['prerequisites'])
    expected.update(manifest['prerequisites'])
    rows.update({r['target']: r for r in data['boot_group']['members'] + [data['runtime_jar']]})
    expected.update({p: r['sha256'] for p, r in rows.items()})
    if set(baseline) - set(expected):
        raise ValueError('candidate deletes baseline files')
    additions = sorted(set(expected) - set(baseline))
    allowed = native.optional_native_additions(manifest, old, additions)
    if set(additions) != set(allowed):
        raise ValueError('only declared native additions may be absent')
    # Bind the entire boot group even if one member happens to match the baseline.
    group = {r['target'] for r in data['boot_group']['members'] + [data['runtime_jar']]}
    changes = [r for p, r in sorted(rows.items()) if p in group or baseline.get(p) != r['sha256']]
    return {'bundle_sha256': bundle.sha(root/'bundle.json'), 'root': str(root),
            'baseline_native': str(baseline_native), 'generation': manifest['generation'],
            'baseline': baseline, 'expected': expected, 'additions': additions,
            'changes': changes, 'reference_paths': {k: sorted(v) for k, v in refs.items()},
            'static_baseline_binding': bundle.sha(baseline_native.parent/'bundle.json') if 'static_checks' in data else None,
            'build_receipt': receipt_check(root, data, manifest), 'rollout_ready': data.get('rollout_ready') is True}


def policy_binding(root):
    repo = Path(__file__).resolve().parents[2]
    files = [repo/'scripts/lab'/n for n in ['u7_executor.py','generation_bundle.py',
             'sweep_bind_deploy.py','deploy_generation.py','deployment_native_gate.py','check_frozen.py',
             'generation_static_checks.py','deployed_class_diff.py','open_site_scan.py']]
    files += [PROVENANCE_REGISTRY, repo/'knowledge/frozen/frozen.json',
              repo/'knowledge/gates/new-native-admissions.json',
              lab_paths.harness()/'knowledge/toolchains/art-r155/image_predeploy_gate.py',
              lab_paths.harness()/bundle.BCP_SWAP_EXCEPTIONS]
    return bundle.digest({str(p): bundle.sha(p) for p in files})


def preflight(root, baseline_native, oatdump):
    policy_before = policy_binding(root)
    plan = prepare(root, baseline_native)
    d = json.loads((Path(root)/'bundle.json').read_text())
    static = None
    if 'image_gate_reference' in d and 'static_checks' not in d:
        raise RuntimeError('effective image replacement requires deployed JAR/native static checks')
    if 'static_checks' in d:
        import generation_static_checks
        baseline_bundle = Path(baseline_native).resolve().parent
        if bundle.sha(baseline_bundle/'bundle.json') != d['static_checks']['baseline_bundle_sha256']:
            raise RuntimeError('static check effective baseline bundle drift')
        policy = json.loads(bundle.member(Path(root),d['static_checks']['policy']).read_text())
        static = generation_static_checks.check(root,baseline_bundle,policy)
        if static['baseline_bundle_sha256'] != d['static_checks']['baseline_bundle_sha256']:
            raise RuntimeError('static effective baseline changed during checks')
        if static['status'] != 'PASS':
            raise RuntimeError('required deployed artifact static check refused: '+json.dumps(static))
    gates = bundle.image_checks(root, oatdump)
    if not all(gates[k] for k in ['G1','G2']):
        raise RuntimeError('required image gate refused: ' + gates['log'])
    tickets = [native_gate.check(Path(root)/d['native']['directory']), native_gate.check(baseline_native)]
    native.check_frozen_package(Path(root)/d['native']['directory'])
    native.check_frozen_package(Path(baseline_native))
    native.check_frozen_restore(plan['expected'])
    native.check_frozen_restore(plan['baseline'], plan['additions'])
    if prepare(root, baseline_native) != plan or policy_binding(root) != policy_before:
        raise RuntimeError('bundle or policy changed during preflight')
    plan.update(image_gates=gates, static_checks=static, native_tickets=tickets, policy_binding=policy_before,
                device_io=False, gates_passed=True)
    plan['deployable'] = plan['rollout_ready'] and plan['build_receipt']['status'] in ('verified', 'verified-with-exception')
    plan['plan_binding'] = bundle.digest(plan)
    return plan


def unchanged(plan):
    current = prepare(plan['root'], plan['baseline_native'])
    for key in current:
        if current[key] != plan[key]: raise RuntimeError('preflight input drift: ' + key)
    if policy_binding(plan['root']) != plan['policy_binding']: raise RuntimeError('policy drift')
    for ticket in plan['native_tickets']: native_gate.assert_unchanged(ticket)


def fingerprints(values, reference_paths):
    return {k: dict(zip(['sha256_12','files'], short_fingerprint(
        '\n'.join(f'{values[p]}  {p}' for p in paths)))) for k, paths in reference_paths.items()}


def baseline_replay_plan(state):
    """Recover only recorded /data-backed baseline overlays, never unrelated mounts."""
    expected = state['plan']['baseline']
    rows = []
    for target, stack in state['before_mounts'].items():
        if not target.startswith(('/system/','/data/app/')) or not any(p == target or p.startswith(target+'/') for p in expected):
            continue
        # Only the visible baseline is required after reboot, not superseded generations.
        for mount in stack[-1:]:
            root = mount['root']
            if not root.startswith(('/local/tmp/','/pr03-74e6-portable/')) or '..' in Path(root).parts:
                raise ValueError('baseline replay requires recorded persistent data source: '+target)
            rows.append(dict(target=target, source='/data'+root, device=mount['device']))
    if not rows:
        raise ValueError('no baseline overlays to replay')
    # Direct file layers must follow their containing directory layers.
    rows.sort(key=lambda r: len(Path(r['target']).parts))
    sources = {}
    for path, digest in expected.items():
        source = path
        for row in rows:
            if path == row['target'] or path.startswith(row['target']+'/'):
                source = row['source']+path[len(row['target']):]
        if source in sources and sources[source] != digest:
            raise ValueError('baseline replay source alias conflict')
        sources[source] = digest
    return rows, sources


def replay_baseline(io, previous, journal):
    """Explicit host-side post-reboot recovery; no persistent startup configuration."""
    journal=Path(journal)
    if journal.exists(): raise RuntimeError('baseline replay journal already exists')
    if previous['serial'] != io.serial or previous['boot_id'] == io.boot:
        raise RuntimeError('baseline replay requires same board and a new boot')
    plan=previous['plan'];io.check_restore(plan)
    rows,sources=baseline_replay_plan(previous)
    io.guard();before=io.mounts()
    for row in rows:
        current=before.get(row['target'],[])
        original=previous['before_mounts'].get(row['target'],[])
        if [r['root'] for r in current] != [r['root'] for r in original[:len(current)]]:
            raise RuntimeError('fresh boot has unexpected baseline overlays')
    actual,absent=io.snapshot(sorted(sources))
    if actual != sources or absent: raise RuntimeError('persistent baseline source SHA mismatch')
    state=dict(schema='westlake-u7-baseline-replay/v1',serial=io.serial,boot_id=io.boot,
               previous_boot=previous['boot_id'],status='prepared',operations=[],before_mounts=before)
    tx=Transaction(io,journal);tx.state=state;tx.record()
    io.stop()
    try:
        for row in rows:
            io.guard(state['boot_id'])
            if not io.stopped():raise RuntimeError('parent restarted during baseline replay')
            op=dict(target=row['target'],remote=row['source'],before=io.mounts().get(row['target'],[]),phase='pending')
            state['operations'].append(op);tx.record()
            io.bind(op['remote'],op['target']);io.assert_owned(op)
            op['phase']='bound';tx.record()
        tx.hashes_match(plan['baseline'])
        io.check_restore(plan)
        io.start(plan['baseline'][HOST])
        state['verification']=io.verify(plan['baseline'],plan['generation'])
        state['fingerprints']=fingerprints(plan['baseline'],plan['reference_paths'])
        state['status']='baseline_restored';tx.record();return state
    except Exception as exc:
        state.update(status='recovery_required',error=str(exc));tx.record()
        # Retain the recorded baseline layers for inspection; never start a mixed tree.
        io.stop()
        raise


class Transaction:
    """State machine independent of transport; every effect has a write-ahead record."""
    def __init__(self, io, journal, plan=None):
        self.io, self.journal, self.plan = io, Path(journal), plan
        self.state = json.loads(self.journal.read_text()) if self.journal.exists() else None

    def record(self):
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        temp = self.journal.with_suffix('.tmp')
        with temp.open('w') as f:
            json.dump(self.state, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        temp.replace(self.journal)
        fd = os.open(self.journal.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def stopped(self):
        self.io.guard(self.state['boot_id'])
        if not self.io.stopped(): raise RuntimeError('parent/child running during transaction')

    def hashes_match(self, expected, absent=()):
        got, missing = self.io.snapshot(sorted(set(expected)|set(absent)), absent)
        if got != expected or set(missing) != set(absent): raise RuntimeError('full identity mismatch')

    def apply(self):
        if self.state: raise RuntimeError('journal exists; use rollback, never overwrite')
        self.io.guard()
        self.hashes_match(self.plan['baseline'], self.plan['additions'])
        before_mounts = self.io.mounts()
        self.state = {'schema':'westlake-u7-transaction/v1','serial':self.io.serial,
                      'boot_id':self.io.boot, 'status':'staging', 'plan':self.plan,
                      'remote':'/data/local/tmp/u7-'+uuid.uuid4().hex,
                      'before_mounts':before_mounts,'operations':[]}
        self.record()
        try:
            staged = self.io.stage(self.plan, self.state['remote'])
            self.io.check_ticket(self.plan)
            self.io.stop()
            self.stopped()
            self.hashes_match(self.plan['baseline'], self.plan['additions'])
            if self.io.mounts() != before_mounts: raise RuntimeError('baseline mounts changed during staging')
            self.state['status'] = 'activating'; self.record()
            for row in self.plan['changes']:
                self.stopped()
                op = dict(row, remote=staged[row['target']], before=self.io.mounts().get(row['target'], []),
                          absent=row['target'] in self.plan['additions'], phase='pending')
                self.state['operations'].append(op); self.record()
                if op['absent']: self.io.placeholder(op['target'])
                self.io.bind(op['remote'], op['target'])
                op['phase'] = 'bound'; self.record()
                self.io.assert_owned(op)
            self.stopped()
            self.hashes_match(self.plan['expected'])
            for op in self.state['operations']: self.io.assert_owned(op)
            self.io.check_ticket(self.plan)
            self.state['status']='verified_stopped';self.record()
            self.io.start(self.plan['expected'][HOST])
            self.state['verification']=self.io.verify(self.plan['expected'],self.plan['generation'])
            for op in self.state['operations']: self.io.assert_owned(op)
            self.state['fingerprints']=fingerprints(self.plan['expected'],self.plan['reference_paths'])
            self.state['status']='active_verified';self.record()
            return self.state
        except Exception as exc:
            self.state['failure']=str(exc);self.record()
            self.rollback()
            raise

    def rollback(self):
        if not self.state: raise RuntimeError('no transaction receipt')
        if self.state['serial'] != self.io.serial: raise RuntimeError('wrong serial')
        self.plan = self.state['plan']
        self.io.guard(self.state['boot_id'])
        # Revalidate original gate-bound rollback input, never candidate expiry.
        try:
            self.io.check_restore(self.plan)
            # Only rollback may recover a known test child's cleanup refusal.
            # Activation keeps its original no-live-child admission guard.
            self.io.stop_for_rollback() if hasattr(self.io, 'stop_for_rollback') else self.io.stop()
            self.stopped()
            self.state['status']='rolling_back';self.record()
            for op in reversed(self.state['operations']):
                self.stopped()
                stack = self.io.mounts().get(op['target'], [])
                if stack != op['before']:
                    self.io.assert_owned(op)
                    op['phase']='unmount_pending';self.record()
                    self.io.unbind(op['target'])
                    if self.io.mounts().get(op['target'], []) != op['before']:
                        raise RuntimeError('underlay stack mismatch')
                if op['absent']: self.io.remove_placeholder(op['target'])
                op['phase']='restored';self.record()
            if self.io.mounts() != self.state['before_mounts']:
                raise RuntimeError('baseline mount stack drift; leave service stopped')
            self.hashes_match(self.plan['baseline'], self.plan['additions'])
            self.state['status']='rollback_verified_stopped';self.record()
            self.io.start(self.plan['baseline'][HOST])
            self.state['rollback_verification']=self.io.verify(self.plan['baseline'],self.plan['generation'])
            self.state['rollback_fingerprints']=fingerprints(self.plan['baseline'],self.plan['reference_paths'])
            self.state['status']='rolled_back';self.record()
            return self.state
        except Exception as exc:
            self.state['rollback_error']=str(exc);self.state['status']='recovery_required';self.record()
            # If verification after start fails, stop again. Never restart a mixed tree.
            try: self.io.stop()
            except Exception as stop_error:
                self.state['stop_error']=str(stop_error);self.record()
            raise


class DeviceIO(native.Deployment):
    """Reuse trusted native stop/start/hash/ps primitives; no complete native deploy call."""
    def __init__(self, serial, lane, out):
        if sys.platform == 'darwin': raise RuntimeError('apply/rollback must run through orb -m a2hlab')
        if serial not in native.SERIALS: raise ValueError('serial not whitelisted')
        source=lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
        spec=importlib.util.spec_from_file_location('trusted_u7_batch',source)
        self.b=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.b)
        self.serial=serial;self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True)
        self.board=self.b.Board(serial,str(lab_paths.tools()/'hdc_mac.sh'),
                    'mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),lane,self.out/'commands')
        self.board.ready();self.boot=self.board.boot

    def guard(self, boot=None):
        self.board.ready()
        if boot is not None and self.board.boot != boot: raise RuntimeError('boot changed; no cross-boot rollback')

    def stopped(self): return not any(r['name']=='appspawn-x' for r in self.ps())

    def stop_for_rollback(self):
        """Bounded cleanup of the observed OrganicMaps residual, then retry stop.

        Do not infer ownership from process NAME alone. BMS must identify the
        test UID, and cold_stop rechecks each PID/PPID/UID before signaling.
        Unknown apps, transport errors and persistent respawns retain the lock.
        No uninstall, service restart, parent signal or guard relaxation here.
        """
        for attempt in range(3):
            self.guard(self.boot)
            try:
                self.stop()
                return
            except RuntimeError as exc:
                if str(exc) != 'other Android children are live; stop them before deployment' or attempt == 2:
                    raise
            pkg = 'app.organicmaps'
            data = self.b.parse_bundle(self.shell('bm dump -n ' + pkg), pkg)
            uid = data['uid']
            rows = self.ps()
            parents = [r['pid'] for r in rows if r['uid'] == 0 and r['ppid'] == 1 and r['name'] == 'appspawn-x']
            residual = [r for r in rows if r['uid'] != 0 and r['name'] == 'appspawn-x']
            if (type(uid) is not int or uid < 20000000 or len(parents) != 1 or not residual
                    or any(r['uid'] != uid or r['ppid'] != parents[0] for r in residual)):
                raise RuntimeError('rollback cleanup cannot identify OrganicMaps residual ownership')
            tag = 'rollback-cold-stop-' + uuid.uuid4().hex
            evidence = self.out / tag
            evidence.mkdir()
            receipt = {'package': pkg, 'uid': uid, 'parent': parents[0],
                       'attempt': attempt + 1, 'before': rows}
            try:
                receipt['quiesced'] = self.b.cold_stop(self.board, pkg, uid, evidence, tag)
                receipt['after'] = self.ps()
            finally:
                (evidence / 'cleanup.json').write_text(json.dumps(receipt, indent=2) + '\n')
            # Re-enter the original stop guard even after a false result: a
            # momentary respawn may disappear. Never proceed on this bool alone.

    def snapshot(self, paths, absent=()):
        result={};missing=[]
        for i in range(0,len(paths),40):
            h,a=self.snapshot_files(paths[i:i+40],absent);result.update(h);missing.extend(a)
        return result,missing

    def mounts(self):
        result={}
        for line in self.shell('cat /proc/self/mountinfo').splitlines():
            f=line.split(); target=f[4]
            if target.startswith(('/system/','/data/app/')):
                result.setdefault(target,[]).append({'id':f[0],'root':f[3],'device':f[2]})
        return result

    def stage(self, plan, remote):
        self.shell('mkdir '+shlex.quote(remote))
        staged={};sources={}
        for row in plan['changes']:
            key=(row['source'],row['sha256'])
            if key not in sources:
                path=remote+'/f'+str(len(sources));sources[key]=path
                stage_file(self.board.send,self.shell,self.hashes,Path(plan['root'])/row['source'],path,row['sha256'],
                           executable=row['target']==HOST or bool((Path(plan['root'])/row['source']).stat().st_mode & 0o111))
            staged[row['target']]=sources[key]
        return staged

    def check_ticket(self, plan): unchanged(plan)

    def check_restore(self, plan):
        old=Path(plan['baseline_native']);ticket=plan['native_tickets'][1]
        native_gate.check(old,expected_binding=ticket['binding'])
        native.check_frozen_package(old);native.check_frozen_restore(plan['baseline'],plan['additions'])

    def placeholder(self, target):
        self.shell('(set -C; : > '+shlex.quote(target)+')')

    def remove_placeholder(self, target):
        got,absent=self.snapshot([target],[target])
        if absent:return
        if got[target]!=EMPTY:raise RuntimeError('owned placeholder modified')
        self.shell('rm '+shlex.quote(target))

    def bind(self, remote, target): bind_file(self.shell,remote,target)
    def unbind(self, target): unbind_file(self.shell,target)

    def assert_owned(self, op):
        stack=self.mounts().get(op['target'],[])
        if len(stack)!=len(op['before'])+1 or stack[:-1]!=op['before'] or stack[-1]['root']!=op['remote'][len('/data'):]:
            raise RuntimeError('mount ownership mismatch: '+op['target'])

    def verify(self, expected, generation):
        # A failed apply may already have desktop-launch captures. Automatic
        # rollback uses this same DeviceIO, and desktop_launch correctly refuses
        # stale settle-0.json. Keep every attempt in a fresh directory instead
        # of overwriting or deleting the earlier evidence.
        verification_out = self.out / ('verification-' + uuid.uuid4().hex)
        verification_out.mkdir()
        rows=[r for r in self.ps() if r['name']=='appspawn-x' and r['uid']==0]
        if len(rows)!=1:raise RuntimeError('parent count != 1')
        parent=rows[0]['pid']
        def view(pid):
            paths={f'/proc/{pid}/root'+p:v for p,v in expected.items()}
            actual,_=self.snapshot(sorted(paths))
            if actual!=paths:raise RuntimeError('process view SHA mismatch')
            if self.hashes([f'/proc/{pid}/exe'])[f'/proc/{pid}/exe']!=expected[HOST]:raise RuntimeError('process executable mismatch')
        view(parent)
        pkg='com.example.helloworld';data=self.b.parse_bundle(self.shell('bm dump -n '+pkg),pkg)
        if not self.b.cold_stop(self.board,pkg,data['uid'],verification_out,'verify-stop'):raise RuntimeError('control cold stop failed')
        remote='/data/local/tmp/u7-smoke-'+uuid.uuid4().hex
        self.shell('mkdir '+remote)
        self.b.desktop_launch(self.board,{'package':pkg,'launch_activity':data['desktop_activity']},remote,verification_out,{'package':pkg})
        time.sleep(4)
        children=[r for r in self.ps() if r['uid']==data['uid'] and r['ppid']==parent and r['name']=='appspawn-x']
        if len(children)!=1:raise RuntimeError('control child count != 1')
        pid=children[0]['pid'];view(pid)
        maps=self.shell(f'cat /proc/{pid}/maps');(verification_out/f'child-{pid}-maps.txt').write_text(maps)
        verdict=native.check_maps(maps,generation)
        if not verdict['passed']:raise RuntimeError('single ART/route openjdk/bridge map gate failed')
        return {'parent':parent,'child':pid,'maps':verdict,'evidence_directory':str(verification_out),
                'screenshot_verdict':'not evaluated'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    for name in ['dry-run','apply','rollback','restore-baseline']:mode.add_argument('--'+name,action='store_true')
    p.add_argument('--from-journal',type=Path)
    p.add_argument('--package',type=Path);p.add_argument('--baseline-native',type=Path)
    p.add_argument('--oatdump');p.add_argument('--journal',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--serial',choices=sorted(native.SERIALS));p.add_argument('--lane',default='cx-t0')
    a=p.parse_args(argv)
    if a.journal and a.journal.resolve()==a.out.resolve():p.error('journal and report must differ')
    device_io=False
    try:
        if a.restore_baseline:
            if not a.from_journal or not a.serial or not a.journal:p.error('restore-baseline requires from-journal, new journal and serial')
            previous=json.loads(a.from_journal.read_text());plan=previous['plan']
            native_gate.check(Path(plan['baseline_native']),expected_binding=plan['native_tickets'][1]['binding'])
            native.check_frozen_restore(plan['baseline'],plan['additions'])
        elif a.rollback:
            if not a.journal or not a.serial:p.error('rollback requires journal and serial')
            state=json.loads(a.journal.read_text());plan=state['plan']
            native_gate.check(Path(plan['baseline_native']),expected_binding=plan['native_tickets'][1]['binding'])
            native.check_frozen_restore(plan['baseline'],plan['additions'])
        else:
            if not a.package or not a.baseline_native:p.error('package and baseline-native required')
            plan=preflight(a.package,a.baseline_native,a.oatdump)
            if a.dry_run:
                native.save(a.out,plan)
                print(json.dumps({k:plan[k] for k in ['device_io','gates_passed','deployable','bundle_sha256']}))
                return 0
            if not plan['deployable']:raise RuntimeError('bundle not rollout-ready or build provenance unknown')
            if not a.journal or not a.serial:p.error('apply requires journal and serial')
        lock_path=lab_paths.workspaces()/'westlake-generation-state'/a.serial/'u7-executor.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        with lock_path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            device_io=True
            io=DeviceIO(a.serial,a.lane,a.out.parent/(a.out.stem+'-device'))
            if a.restore_baseline:
                result=replay_baseline(io,previous,a.journal)
            else:
                tx=Transaction(io,a.journal,plan)
                result=tx.rollback() if a.rollback else tx.apply()
        native.save(a.out,result);print(result['status']);return 0
    except Exception as exc:
        native.save(a.out,{'status':'rejected','error':str(exc),'device_io':device_io})
        print(str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
