#!/usr/bin/env python3
"""Reviewed, fail-closed 61b v1/v2 seal workflow; default v1 preview."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[2]
SERIAL = '61b0657200000000000000000324012c'
BASELINE_SERIAL = '5cd1e3dd00000000000000000923012c'
T3_SIGNOFF_SHA = '0e9b825a0ccbfcbe6af0bc1ccd7f93d55d323e1869b8ecdc957a7591048aa387'
T3_SIGNOFF_SUFFIX = 'benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json'
ROOT = '/data/westlake-demo/u13'
BOOT = 'cat /proc/sys/kernel/random/boot_id'
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOARD_PATH = re.compile(r'/[A-Za-z0-9_./+-]+\Z')
PROVIDERS = ('lock_check', 'toutiao_slot', 'reboot_inputs', 'acceptance',
             'regression_review', 'seal_snapshot')
TOOLS = {'snapshot', 'diff', 'sepolicy', 'reboot_sim', 'post_reboot', 'regress', 'seal'}
INPUTS = {'baseline_319', 'recover_table', 'policy', 'recipe', 'manifest', 'tiers',
          'install_index', 'smoke', 'overlays', 'signoff_5cd', 'regression_admission', 'snapshot_plan'}
DEFAULT = REPO / 'benchmark/2026-10-10-demo-seal-61b/plan-template.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand(value):
    return os.path.expanduser(os.path.expandvars(str(value).replace('$REPO', str(REPO))))


def pinned(reference):
    require(isinstance(reference, dict) and SHA.fullmatch(str(reference.get('sha256', ''))),
            'unbound SHA/reference')
    path = Path(expand(reference['path']))
    require(path.is_file() and not path.is_symlink() and sha(path) == reference['sha256'],
            'missing/drifted input: ' + str(path))
    return path


def board_path(value):
    require(isinstance(value, str) and BOARD_PATH.fullmatch(value) and
            '..' not in value.split('/'), 'unsafe board path')
    return value


def regression_reference(plan, kind):
    require(kind in ('5cd', '61b-t3'), 'unknown regression reference')
    reference = plan.get('reference', {})
    require(reference.get('kind') == kind, 'reference differs from authorized plan')
    return reference


def validate_reference(plan, kind, keys):
    reference = regression_reference(plan, kind)
    signoff_path = pinned(reference['signoff'])
    signoff = read(signoff_path)
    serial = BASELINE_SERIAL if kind == '5cd' else SERIAL
    require(signoff.get('board') == serial and set(signoff.get('verdicts', {})) == set(keys),
            '128-key signed ' + kind + ' baseline required')
    require(Path(expand(reference['baseline_t3'])).is_dir(), 'reference record directory missing')
    if kind == '5cd':
        require(reference['signoff'] == plan['inputs']['signoff_5cd'] and
                expand(reference['baseline_t3']) == expand(plan['baseline_5cd_t3']), 'ambiguous 5cd reference')
    else:
        require(signoff_path.as_posix().endswith('/' + T3_SIGNOFF_SUFFIX) and
                reference['signoff']['sha256'] == T3_SIGNOFF_SHA, '61b-t3 must use exact canonical t3 signoff SHA/path')
        index = read(pinned(reference['record_index']))
        require(index.get('signoff_sha256') == T3_SIGNOFF_SHA and set(index.get('records', {})) == set(keys),
                't3 record index binding mismatch')
        for key, item in index['records'].items():
            record = read(pinned(item['record']))
            require(record.get('key') == key and record.get('serial') == SERIAL and
                    item.get('batch') == signoff['verdicts'][key]['batch'], 't3 record identity mismatch: ' + key)
            pinned(item['image'])
        notes = read(pinned(reference['enforcing_prerun']))
        require(notes.get('serial') == BASELINE_SERIAL and notes.get('signoff_sha256') == T3_SIGNOFF_SHA and
                len(notes.get('keys', {})) == 89 and set(notes['keys']) <= set(keys), '89-key Enforcing notes mismatch')
        require(pinned(notes['enforce']).read_text().strip() == '1', '5cd capture was not Enforcing')
        report = read(pinned(notes['comparison']))
        observed = {row['key']: row for row in report['keys'] if row['category'] != 'missing'}
        require(report.get('signoff_sha256') == T3_SIGNOFF_SHA and set(observed) == set(notes['keys']),
                '5cd notes/comparison membership mismatch')
        for key, item in notes['keys'].items():
            record = read(pinned(item['record']))
            require(record.get('key') == key and record.get('serial') == BASELINE_SERIAL and
                    bool(record.get('finished_at')) and item['category'] == observed[key]['category'] and
                    item['signature'] == observed[key]['signature'] and
                    item['reason'] == observed[key]['reason'] and item['semantic'] == observed[key]['semantic'] and
                    record.get('apk_sha256') == item['signature']['apk_sha256'], '5cd note identity mismatch: ' + key)
    return reference


def annotate_enforcing(comparison, notes):
    count = 0
    for row in comparison['keys']:
        prior = notes['keys'].get(row['key'])
        suspect = bool(row.get('category') == 'changed' and prior and prior['category'] == 'changed' and
                       prior['signature'].get('package') and SHA.fullmatch(str(prior['signature'].get('apk_sha256', ''))) and
                       all(row.get('signature', {}).get(field) == prior['signature'].get(field)
                           for field in ('package', 'apk_sha256')))
        row['env_enforcing_suspect'] = suspect
        if suspect:
            row['enforcing_annotation'] = dict(record=prior['record'], prior_reason=prior['reason'],
                    prior_semantic=prior['semantic'], reason_overlap=sorted(set(row.get('reason', [])) & set(prior['reason'])),
                    verdict='outer-image-review-required; no automatic exemption')
            count += 1
    comparison['enforcing_annotation'] = dict(suspect_keys=count, automatic_exemptions=0,
                scope='5cd capture enforce=1; changed is evidence triage, not an adverse UI verdict')
    return comparison


def live_binds(text, targets):
    require(bool(text.strip()), 'empty mountinfo is not a clean boot')
    found = []
    for line in text.splitlines():
        fields = line.split()
        require(len(fields) >= 10 and ' - ' in line, 'malformed mountinfo')
        root, target = (re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)
                        for value in fields[3:5])
        if any(target == path or target.startswith(path.rstrip('/') + '/') for path in targets) or \
                root.startswith('/westlake-demo/u13/sources') or root.startswith(ROOT + '/sources'):
            found.append({'root': root, 'target': target, 'line': line})
    return found


def archived_base(expected):
    prefix = '/system/android/'
    members = {ROOT + '/sources/seq1/' + target[len(prefix):]: digest
               for target, digest in expected.items() if target.startswith(prefix)}
    require(bool(members), 'signed /system/android baseline missing')
    return members


class Transport:
    def __init__(self, out, timeout):
        self.out, self.timeout, self.counter = Path(out), timeout, 0

    def run(self, name, argv, env=None):
        self.counter += 1
        stem = self.out / ('%03d-%s' % (self.counter, name))
        with stem.with_suffix('.stdout').open('xb') as stdout, stem.with_suffix('.stderr').open('xb') as stderr:
            try:
                result = subprocess.run(argv, stdout=stdout, stderr=stderr,
                                        timeout=min(self.timeout, 15) if name.startswith('wait-') else self.timeout,
                                        env=dict(os.environ, **(env or {})))
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                stderr.write(str(error).encode())
                code = 124 if isinstance(error, subprocess.TimeoutExpired) else 125
        text = stem.with_suffix('.stdout').read_text(errors='backslashreplace')
        stem.with_suffix('.json').write_text(json.dumps(dict(argv=argv, exit=code,
                stdout_sha256=sha(stem.with_suffix('.stdout')),
                stderr_sha256=sha(stem.with_suffix('.stderr'))), indent=2) + '\n')
        return code, text


class Workflow:
    def __init__(self, plan, out, transport=None, preview=False, plan_sha='', sleep=time.sleep, plan_path=None, mode='v1', reference='5cd'):
        self.plan, self.out, self.transport = plan, Path(out), transport
        self.preview, self.plan_sha, self.sleep = preview, plan_sha, sleep
        self.boot_id = '<boot-id-after-autonomous-reboot>'
        self.initial_boot = '<boot-id-before-bare-reboot>'
        self.bare_boot = '<bare-boot-id>'
        self.events = []
        self.plan_path = plan_path
        require(mode in ('v1', 'v2'), 'invalid seal mode')
        self.mode = mode
        self.reference_kind = reference
        self.reference = regression_reference(plan, reference)
        # SELinux acceptance is plan-driven: the plan MUST declare selinux_mode (validate() enforces it).
        # 'enforcing' -> getenforce must read 'Enforcing'; 'permissive' -> 'Permissive'. Default enforcing.
        self.selinux_mode = plan.get('selinux_mode', 'enforcing')
        self.expected_enforce = {'enforcing': 'Enforcing', 'permissive': 'Permissive'}.get(self.selinux_mode, 'Enforcing')

    def command(self, name, argv, criterion, allowed=(0,), env=None):
        self.events.append(name)
        print(name + ': ' + shlex.join(argv) + '\n  REQUIRE: ' + criterion, flush=True)
        if self.preview:
            return 0, ''
        code, output = self.transport.run(name, argv, env)
        require(code in allowed, '%s exit=%s; STOP, preserve state/logs' % (name, code))
        return code, output

    def shell(self, name, command, criterion, allowed=(0,)):
        return self.command(name, [self.plan.get('hdc', 'hdc'), '-t', SERIAL, 'shell', command],
                            criterion, allowed)

    def tool(self, name):
        ref = self.plan['tools'][name]
        return ref['path'] if self.preview else expand(ref['path'])

    def input(self, name):
        value = self.plan['inputs'][name]['path']
        return value if self.preview else expand(value)

    def provider(self, name, criterion):
        spec = self.plan['providers'][name]
        argv = [(value if self.preview else expand(value))
                for value in (spec.get('argv') or ['<outer-bind:' + name + '>'])]
        env = dict(DEMO_SEAL_OUT=str(self.out), DEMO_SEAL_SERIAL=SERIAL,
                   DEMO_SEAL_BOOT_ID=self.boot_id, DEMO_SEAL_PLAN_SHA=self.plan_sha,
                   DEMO_SEAL_STEP=name, DEMO_SEAL_PLAN=str(self.plan_path or ''))
        env.update(DEMO_SEAL_REFERENCE=self.reference_kind,
                   DEMO_SEAL_REFERENCE_SIGNOFF_SHA=str(self.reference['signoff']['sha256']))
        self.command(name, argv, criterion, env=env)
        if self.preview:
            return {}
        report = read(self.out / (name + '.json'))
        require(report.get('serial') == SERIAL and report.get('plan_sha256') == self.plan_sha,
                name + ': receipt identity/binding mismatch')
        return report

    def boot(self, name):
        _, output = self.shell(name, BOOT, 'nonempty canonical boot UUID')
        if self.preview:
            return '<' + name + '>'
        value = output.strip()
        require(UUID.fullmatch(value), 'invalid boot_id')
        return value

    def wait_boot(self, name, previous):
        if self.preview:
            self.shell(name, BOOT + '; param get bootevent.boot.completed',
                       'bounded reconnect, boot_id differs from ' + previous + '; boot.completed=true')
            return '<' + name + '>'
        deadline = time.monotonic() + self.plan['boot_timeout_seconds']
        while time.monotonic() < deadline:
            code, output = self.command(name, [self.plan['hdc'], '-t', SERIAL, 'shell',
                    BOOT + '; param get bootevent.boot.completed'],
                    'changed boot UUID and ready=true; transport retry only', allowed=(0, 1, 124, 125, 255))
            lines = output.strip().splitlines()
            if code == 0 and len(lines) == 2 and UUID.fullmatch(lines[0]) and lines[0] != previous and lines[1] == 'true':
                return lines[0]
            self.sleep(2)
        raise ValueError(name + ': no changed, ready boot before deadline')

    def assert_no_binds(self):
        for view in ('self', '1'):
            _, text = self.shell('no-live-recover-bind-' + view, 'cat /proc/' + view + '/mountinfo',
                                 'no mount at/below any of 56 recover targets, in shell AND init view')
            if not self.preview:
                table = read(self.input('recover_table'))
                targets = [board_path(row['target']) for row in table['recover_layers']]
                found = live_binds(text, targets)
                require(not found, 'LIVE_BIND_REFUSE installer: ' + json.dumps(found))

    def assert_bare_base(self):
        archive = ROOT + '/sources/seq1'
        expected = {} if self.preview else archived_base(read(self.input('baseline_319'))['expected'])
        _, inventory = self.shell('bare-seq1-inventory', 'test -d ' + archive + ' && test ! -L ' + archive +
                                  ' && find ' + archive + ' -type f',
                                  'seq1 membership/count exactly derived from pinned signed319 /system/android subset (246 on current61b)')
        if not self.preview:
            paths = inventory.splitlines()
            require(len(paths) == len(set(paths)) and set(paths) == set(expected),
                    'BARE_BASE_REFUSE seq1 membership: ' + json.dumps(dict(
                        expected_count=len(expected), actual_count=len(paths),
                        missing=sorted(set(expected) - set(paths)), extra=sorted(set(paths) - set(expected)))))
        actual = {}
        groups = [list(expected)[offset:offset + 24] for offset in range(0, len(expected), 24)] or [['<signed-seq1-paths>']]
        for group in groups:
            _, text = self.shell('bare-seq1-sha', 'sha256sum ' + ' '.join(group),
                                 'every seq1 relative member equals signed /system/android SHA, not merely file count')
            if not self.preview:
                for line in text.splitlines():
                    match = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
                    require(match is not None and match[2] not in actual, 'BARE_BASE_REFUSE malformed/duplicate seq1 SHA output')
                    actual[match[2]] = match[1]
        if not self.preview:
            differences = {path: dict(expected=expected.get(path), actual=actual.get(path))
                           for path in sorted(set(expected) | set(actual)) if expected.get(path) != actual.get(path)}
            require(actual == expected, 'BARE_BASE_REFUSE seq1 SHA mismatch: ' + json.dumps(differences))
        _, physical = self.shell('bare-physical-inventory',
                                 'test -d /system/android && test ! -L /system/android && find /system/android -type f',
                                 'physical /system/android has exactly0 files; signed seq1 is nonempty so installer must REUSE')
        require(self.preview or not physical.splitlines(), 'BARE_BASE_REFUSE physical /system/android not empty: ' + physical)
        if not self.preview:
            print('BARE_BASE: seq1_files=' + str(len(expected)) + ' sha_diff={} physical_files=0 decision=REUSE', flush=True)

    def snapshot(self, phase):
        self.command('snapshot-' + phase, ['python3', self.tool('snapshot'), SERIAL,
                     '--hdc', self.plan['hdc'], '--plan', self.input('snapshot_plan'),
                     '--out', str(self.out / phase), '--label', 'seal-' + self.mode + '-' + phase],
                     'collection complete, declared targets complete, stable current boot; read-only')
        if not self.preview:
            doc = read(self.out / phase / 'snapshot.json')
            require(doc.get('serial') == SERIAL and doc.get('complete') is True and doc.get('boot_stable') is True and
                    doc.get('boot_id') == self.boot_id,
                    'incomplete snapshot')

    def reviewed(self, name, checks):
        report = self.provider(name, 'fresh outer-signed UI/observation receipt; checks=' + ','.join(checks) +
                               '; not process-alive or command PASS')
        if self.preview:
            return
        require(report.get('boot_id') == self.boot_id and report.get('approved_by') == 'outer(claude)' and
                bool(report.get('approved_at')) and report.get('no_mac_repair') is True,
                name + ': stale/unsigned/repaired observations')
        require(all(report.get('checks', {}).get(check) is True for check in checks), name + ': missing/failed criterion')
        references = report.get('evidence', [])
        require(bool(references), name + ': evidence required')
        for reference in references:
            pinned(reference)
        if name == 'regression_review':
            require(report.get('comparison_sha256') == sha(self.out / 'regression/comparison.json'),
                    'outer review not bound to this comparison')
            require(report.get('baseline_serial') == (BASELINE_SERIAL if self.reference_kind == '5cd' else SERIAL),
                    'outer review baseline serial/reference mismatch')
            if self.reference_kind == '61b-t3':
                require(report.get('reference_kind') == self.reference_kind and
                        report.get('signoff_sha256') == T3_SIGNOFF_SHA, 'outer review t3 signoff binding mismatch')

    def run(self):
        lock = self.provider('lock_check', 'fresh held state: no conflicting owner; outer-approved window, no implicit lock stealing')
        if not self.preview:
            require(lock.get('no_conflict') is True, 'lock conflict')
        self.initial_boot = self.boot('initial-boot')
        self.boot_id = self.initial_boot
        _, enforce = self.shell('pre-enforcing', 'getenforce', 'getenforce == plan selinux_mode (' + self.expected_enforce + ')')
        if not self.preview:
            require(enforce.strip() == self.expected_enforce,
                    'getenforce ' + enforce.strip() + ' != plan selinux_mode ' + self.expected_enforce)
        expected = {} if self.preview else read(self.input('baseline_319'))['expected']
        groups = [list(expected)[offset:offset + 24] for offset in range(0, len(expected), 24)] or [['<319-signed-paths>']]
        actual = {}
        for group in groups:
            _, text = self.shell('pre-319', 'sha256sum ' + ' '.join(group), '319 signed paths, diff={}, absent=0')
            if not self.preview:
                for line in text.splitlines():
                    match = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
                    require(match is not None and match[2] not in actual, 'malformed/duplicate identity output')
                    actual[match[2]] = match[1]
        if not self.preview:
            require(actual == expected and len(actual) == 319, '319 baseline mismatch')
        before = self.boot('pre-disable-boot')
        require(self.preview or before == self.initial_boot, 'boot changed during readonly preflight')
        self.shell('disable', 'test -d ' + ROOT + ' && touch ' + ROOT + '/DISABLED && test -f ' + ROOT + '/DISABLED',
                   'DISABLED exists before bare reboot')
        self.command('bare-reboot', [self.plan['hdc'], '-t', SERIAL, 'target', 'boot'], 'target boot, never shell reboot')
        self.bare_boot = self.wait_boot('wait-bare-boot', before)
        self.boot_id = self.bare_boot
        self.shell('bare-disabled', 'test -f ' + ROOT + '/DISABLED', 'boot worker remains disabled')
        self.assert_no_binds()
        _, installer_sha = self.shell('installer-sha', 'sha256sum ' + self.plan['installer']['board_path'],
                                      'exact reviewed guard-ready installer SHA')
        if not self.preview:
            require(installer_sha.split() == [self.plan['installer']['sha256'], self.plan['installer']['board_path']],
                    'staged installer drift')
        self.assert_no_binds()
        self.assert_bare_base()
        installer = self.plan['installer']
        # permissive plan -> install the v3 recover variant (adds the default-OFF selinux-mode switch) via the SAME
        # safe sequence (DISABLED -> bare boot -> assert_bare_base -> installer REUSE); no extra installer re-run.
        # enforcing plan -> no env, installer defaults to RECOVER_VARIANT=v2 (unchanged behaviour).
        recover_env = 'RECOVER_VARIANT=v3 ' if self.selinux_mode == 'permissive' else ''
        command = 'DEPLOY=' + shlex.quote(installer['deploy']) + ' WITH_BOAT=' + ('1' if self.mode == 'v2' else '0') + ' ALLOW_REMOUNT=1 ' + recover_env + '/system/bin/sh ' + shlex.quote(installer['board_path'])
        _, installed = self.shell('installer', command, 'guard-ready installer; ARCHIVE only on bare no-bind boot; INSTALL_OK')
        require(self.preview or 'INSTALL_OK' in installed.splitlines(), 'missing installer success receipt')
        slot = self.provider('toutiao_slot', 'after base installer: uid-dynamic reconcile/readback; immutable six-name exclusions; ENABLE=rm DISABLED + place cfg; no app launch')
        if not self.preview:
            require(slot.get('enabled') is True and slot.get('boot_id') == self.bare_boot and
                    slot.get('uid_mode') == 'installed-host-dynamic' and slot.get('reconcile_checked') is True and
                    slot.get('immutable_preserved') is True, 'Toutiao dynamic slot not verified/enabled on bare boot')
        if self.selinux_mode == 'permissive':
            # opt-in BEFORE enable so the first recover-v3 run (next boot) consumes it after bind+labels.
            _, mode_rb = self.shell('selinux-mode-file',
                    'echo permissive > ' + ROOT + '/selinux-mode && cat ' + ROOT + '/selinux-mode',
                    'opt-in ' + ROOT + '/selinux-mode=permissive written + read back')
            require(self.preview or mode_rb.strip() == 'permissive', 'selinux-mode file readback != permissive')
        self.shell('enable', 'rm -f ' + ROOT + '/DISABLED && test ! -e ' + ROOT + '/DISABLED', 'U13 recovery ENABLE')
        self.snapshot('pre')
        self.command('sepolicy-gate', ['python3', self.tool('sepolicy'), '--policy', self.input('policy'),
                     '--recipe', self.input('recipe'), '--evidence', str(self.out / 'sepolicy.json')],
                     'fresh policy/recipe proofs; exit 0, no setenforce')
        self.provider('reboot_inputs', 'prepare eight pinned simulator inputs using this pre snapshot and physical underlay evidence')
        code, _ = self.command('reboot-sim-advisory', ['python3', self.tool('reboot_sim'),
                    '--inputs', str(self.out / 'reboot-inputs.json'), '--out', str(self.out / 'prediction')],
                    'advisory table; rc1 FAIL/UNKNOWN is recorded, not a safety PASS; rc2 stops', allowed=(0, 1))
        if not self.preview:
            require((self.out / 'prediction/prediction.json').is_file(), 'missing advisory prediction report')
            print('ADVISORY exit=' + str(code) + '; not a reboot-safety authorization', flush=True)
        before = self.boot('pre-autonomous-boot')
        require(self.preview or before == self.bare_boot, 'unexpected boot before final reboot')
        self.command('autonomous-reboot', [self.plan['hdc'], '-t', SERIAL, 'target', 'boot'],
                     'no Mac replay, deployment, label fix, provisioning or background launch after reboot')
        self.boot_id = self.wait_boot('wait-autonomous-boot', before)
        _, enforce = self.shell('post-enforcing', 'getenforce', 'getenforce == plan selinux_mode (' + self.expected_enforce + ')')
        require(self.preview or enforce.strip() == self.expected_enforce,
                'post reboot getenforce ' + enforce.strip() + ' != plan selinux_mode ' + self.expected_enforce)
        if self.selinux_mode == 'permissive':
            # recover-v3 records the opt-in + read-back in the receipt; verify both (v2 receipts omit these fields).
            _, receipt_env = self.shell('post-receipt-selinux', 'cat ' + ROOT + '/receipt.env',
                    'receipt records selinux_requested=permissive + selinux_mode=Permissive')
            if not self.preview:
                lines = receipt_env.splitlines()
                require('selinux_requested=permissive' in lines and 'selinux_mode=Permissive' in lines,
                        'receipt selinux fields not permissive/Permissive: ' + receipt_env)
        _, dmesg = self.shell('post-dmesg', 'dmesg', 'zero invalid:appspawn-x entries')
        require(self.preview or not re.search(r'invalid\s*:\s*appspawn-x', dmesg), 'init INVALID appspawn-x')
        checks = ('parent_init', 'socket_0660', 'hw_t20_lit', 'zz_t20_lit', 'toutiao_desktop_click_refresh_article')
        if self.mode == 'v2':
            checks += ('boat_five_touch_lap',)
        self.reviewed('acceptance', checks)
        _, processes = self.shell('post-parent', 'ps -A -o PID,PPID,UID,NAME', 'exactly one root appspawn-x, PPID=1 after foreground taps')
        if not self.preview:
            parents = [line.split() for line in processes.splitlines() if line.split() and line.split()[-1] == 'appspawn-x']
            require(len(parents) == 1 and len(parents[0]) == 4 and parents[0][1:3] == ['1', '0'], 'appspawn-x parent/UID mismatch')
        _, socket = self.shell('post-socket', "stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX",
                               '660:0:6005:u:object_r:appspawn_socket:s0')
        require(self.preview or socket.strip() == '660:0:6005:u:object_r:appspawn_socket:s0', 'socket identity mismatch')
        _, dmesg = self.shell('post-apps-dmesg', 'dmesg', 'zero invalid:appspawn-x after foreground acceptance')
        require(self.preview or not re.search(r'invalid\s*:\s*appspawn-x', dmesg), 'init INVALID after acceptance')
        self.snapshot('post')
        self.command('snapshot-diff', ['python3', self.tool('diff'), str(self.out / 'pre/snapshot.json'),
                    str(self.out / 'post/snapshot.json'), '--json', str(self.out / 'state-diff.json')],
                    'raw readonly before/after difference; review, not automatic UI success')
        round_dir = self.out / 'round128'
        self.command('prepare-128', ['python3', self.tool('post_reboot'), '--serial', SERIAL,
                    '--out', str(round_dir), '--boot-before', before, '--manifest', self.input('manifest'),
                    '--tiers', self.input('tiers'), '--install-index', self.input('install_index'),
                    '--smoke', self.input('smoke')], '128 installed-only keys prepared; no reinstall/replay')
        self.command('run-128', ['python3', self.tool('post_reboot'), '--serial', SERIAL,
                    '--out', str(round_dir), '--execute', '--authorization', self.plan['window_authorization']],
                    '128 records and screenshots on same reboot; runner owns per-window lock protocol')
        signoff_path = self.reference['signoff']['path']
        baseline_t3 = self.reference['baseline_t3']
        self.command('regress-vs-' + self.reference_kind, ['python3', self.tool('regress'), str(round_dir / 'final'),
                    '--signoff', signoff_path if self.preview else expand(signoff_path),
                    '--baseline-t3', baseline_t3 if self.preview else expand(baseline_t3),
                    '--out', str(self.out / 'regression')], 'signed ' + self.reference_kind + ' reference; triage is not an outer UI verdict')
        if not self.preview:
            comparison = read(self.out / 'regression/comparison.json')
            keys = {row['key'] for row in comparison['keys']}
            expected_keys = {row['key'] for row in read(self.input('manifest'))['apps'] if row.get('install') is not False}
            require(len(expected_keys) == 128 and len(comparison['keys']) == 128 and keys == expected_keys and
                    not comparison.get('extra_keys') and comparison['summary']['missing'] == 0,
                    '128 regression membership/capture mismatch')
            require(comparison.get('signoff_sha256') == self.reference['signoff']['sha256'], 'comparison signoff SHA mismatch')
            (self.out / 'regression/comparison.raw.json').write_bytes((self.out / 'regression/comparison.json').read_bytes())
            comparison['reference'] = self.reference
            if self.reference_kind == '61b-t3':
                validate_reference(self.plan, self.reference_kind, expected_keys)
                index = read(pinned(self.reference['record_index']))['records']
                for row in comparison['keys']:
                    require(Path(expand(row['baseline_record'])).resolve() ==
                            Path(expand(index[row['key']]['record']['path'])).resolve(),
                            'comparison did not use pinned t3 record: ' + row['key'])
                annotate_enforcing(comparison, read(pinned(self.reference['enforcing_prerun'])))
            (self.out / 'regression/comparison.json').write_text(json.dumps(comparison, indent=2) + '\n')
        elif self.reference_kind == '61b-t3':
            print('ANNOTATE: changed key also changed in pinned 5cd Enforcing prerun => env_enforcing_suspect; retain changed, outer image review required', flush=True)
        self.reviewed('regression_review', ('all_128_observed',
                      'no_regression_vs_5cd' if self.reference_kind == '5cd' else 'no_regression_vs_reference', 'identity_unchanged'))
        require(self.preview or self.boot('final-boot') == self.boot_id, 'boot drift during acceptance/regression')
        receipt = self.provider('seal_snapshot', 'fresh live-readonly seal snapshot: complete package/APK inventory, runtime/boot/overlay hashes')
        if not self.preview:
            require(receipt.get('boot_id') == self.boot_id, 'seal snapshot boot mismatch')
            captured = read(self.out / 'seal-snapshot.json')
            require(captured.get('serial') == SERIAL and captured.get('boot_before') == self.boot_id and
                    captured.get('boot_after') == self.boot_id, 'seal snapshot identity drift')
        self.command('build-seal', ['python3', self.tool('seal'), '--snapshot', str(self.out / 'seal-snapshot.json'),
                    '--overlays', self.input('overlays'), '--manifest', self.input('manifest'),
                    '--out', str(self.out / 'seal.json')], self.mode + (' admitted Boat + Route B layers' if self.mode == 'v2' else ' Route B active, Boat absent') + '; compiler success is not new live acceptance')
        if not self.preview:
            sealed = read(self.out / 'seal.json')
            require(sealed.get('seal_stage') == self.mode, 'compiled seal mode mismatch')
            sealed['regression_reference'] = dict(self.reference,
                    baseline_serial=BASELINE_SERIAL if self.reference_kind == '5cd' else SERIAL,
                    comparison_sha256=sha(self.out / 'regression/comparison.json'),
                    outer_review_sha256=sha(self.out / 'regression_review.json'))
            sealed['selinux_mode'] = self.selinux_mode
            (self.out / 'seal.json').write_text(json.dumps(sealed, indent=2) + '\n')


def validate(plan, authorization, plan_sha, mode='v1', reference='5cd'):
    require(plan.get('schema') == 'demo-seal-61b-orchestration/v1' and plan.get('serial') == SERIAL and
            plan.get('execution_enabled') is True, 'disabled/unapproved plan')
    require(not plan.get('pending'), 'pending bindings remain; no board writes authorized')
    require(plan.get('mode') == mode and mode in ('v1', 'v2'), 'mode differs from authorized plan')
    require(plan.get('selinux_mode') in ('enforcing', 'permissive'),
            'plan must explicitly declare selinux_mode (enforcing|permissive)')
    approval = read(authorization)
    require(approval.get('approved_by') == 'outer(claude)' and bool(approval.get('approved_at')) and
            approval.get('serial') == SERIAL and approval.get('plan_sha256') == plan_sha and
            approval.get('execution_authorized') is True, 'outer window authorization mismatch')
    require(bool(plan.get('window_authorization')), 'runner authorization reference missing')
    require(plan.get('driver_sha256') == sha(Path(__file__)), 'orchestrator SHA not bound')
    require(set(plan.get('tools', {})) == TOOLS and set(plan.get('inputs', {})) == INPUTS and
            set(plan.get('providers', {})) == set(PROVIDERS), 'missing/extra tool/input/provider bindings')
    pinned(plan['toutiao_slot']['placement'])
    require(1 <= plan['boot_timeout_seconds'] <= 600 and 1 <= plan['command_timeout_seconds'] <= 10800,
            'timeouts out of bounds')
    references = list(plan['tools'].values()) + [reference for name, reference in plan['inputs'].items()
                                                if (name != 'regression_admission' or mode == 'v2') and
                                                (name != 'signoff_5cd' or reference == '5cd')]
    for bound_input in references:
        pinned(bound_input)
    expected = read(pinned(plan['inputs']['baseline_319']))['expected']
    require(len(expected) == 319 and all(SHA.fullmatch(value) for value in expected.values()), 'signed 319 inventory required')
    for value in expected:
        board_path(value)
    archived_base(expected)
    table = read(pinned(plan['inputs']['recover_table']))
    targets = [board_path(row['target']) for row in table['recover_layers']]
    require(len(targets) == 56 and len(set(targets)) == 56 and '/system/android' in targets,
            '56 unique recovery targets required')
    overlays = read(pinned(plan['inputs']['overlays']))
    require(overlays.get('seal_stage') == mode and len(overlays.get('items', [])) == 2 and
            {row.get('id') for row in overlays['items']} == {'boatattack', 'toutiao-route-b'} and
            next(row for row in overlays['items'] if row['id'] == 'toutiao-route-b').get('state') == 'active',
            'active Route B and explicit seal mode required')
    boat = next(row for row in overlays['items'] if row['id'] == 'boatattack')
    require(boat.get('state') == ('active' if mode == 'v2' else 'absent') and
            (mode == 'v2' or (not boat.get('files') and bool(boat.get('reason')))), 'Boat layer disagrees with v1/v2 mode')
    manifest = read(pinned(plan['inputs']['manifest']))
    keys = [row['key'] for row in manifest['apps'] if row.get('install') is not False]
    require(len(keys) == 128 and len(set(keys)) == 128, '128 unique manifest keys required')
    validate_reference(plan, reference, keys)
    installer = plan['installer']
    board_path(installer['board_path'])
    board_path(installer['deploy'])
    require(sha(pinned(installer['source'])) == installer['sha256'], 'installer source SHA mismatch')
    guard = read(pinned(installer['guard_approval']))
    require(guard.get('approved_by') == 'outer(claude)' and guard.get('live_bind_fail_closed') is True and
            guard.get('bare_boot_supported') is True and guard.get('installer_sha256') == installer['sha256'],
            'guard-ready bare-boot installer approval pending')
    if mode == 'v2':
        regression = read(pinned(plan['inputs']['regression_admission']))
        require(regression.get('approved_by') == 'outer(claude)' and regression.get('overlay_aware') is True and
                regression.get('post_reboot_sha256') == plan['tools']['post_reboot']['sha256'] and
                regression.get('overlays_sha256') == plan['inputs']['overlays']['sha256'],
                'v2 effective identity runner admission pending; original U13 hook rejects Boat overlay')
    for name in PROVIDERS:
        provider = plan['providers'][name]
        require(isinstance(provider.get('argv'), list) and bool(provider['argv']) and
                all(isinstance(value, str) and value for value in provider['argv']), 'pending provider: ' + name)
        paths = [str(pinned(reference)) for reference in provider.get('pins', [])]
        require(paths and any(value in paths for value in map(expand, provider['argv'])), 'unpinned provider: ' + name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT)
    parser.add_argument('--serial', choices=('61b', SERIAL), default='61b')
    parser.add_argument('--mode', choices=('v1', 'v2'), default='v1')
    parser.add_argument('--reference', choices=('5cd', '61b-t3'), default='5cd')
    parser.add_argument('--out', type=Path, default=Path('<fresh-output-directory>'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args(argv)
    plan = None
    try:
        require(not (args.execute and args.dry_run), 'choose dry-run or execute')
        plan = read(args.plan)
        require(plan.get('serial') == SERIAL, '61b-only plan')
        plan_sha = sha(args.plan)
        if not args.execute:
            print('DRY-RUN: commands/criteria only; zero transport, locks and output writes; pending bindings do not imply readiness')
            Workflow(plan, args.out, preview=True, plan_sha=plan_sha, mode=args.mode, reference=args.reference).run()
            return 0
        require(args.authorization is not None and str(args.out) != '<fresh-output-directory>', 'authorization and fresh --out required')
        validate(plan, args.authorization, plan_sha, args.mode, args.reference)
        args.out.mkdir(parents=True, exist_ok=False)
        workflow = Workflow(plan, args.out, Transport(args.out, plan['command_timeout_seconds']),
                            plan_sha=plan_sha, plan_path=args.plan.absolute(), mode=args.mode, reference=args.reference)
        try:
            workflow.run()
        finally:
            (args.out / 'steps.json').write_text(json.dumps(workflow.events, indent=2) + '\n')
        print('SEAL_COMPILED: ' + str(args.out / 'seal.json'))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('SEAL-STOP: ' + str(error), file=sys.stderr)
        print('RECOVERY (not executed): fresh cx-t0 U13 61b native-ticket replay OR reviewed signed-bundle repave; preserve logs/lock, outer review first', file=sys.stderr)
        if plan:
            print(json.dumps(plan.get('recovery_entries', {})), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
