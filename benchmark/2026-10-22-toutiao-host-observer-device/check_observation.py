#!/usr/bin/env python3
"""T42 read-only receipt checker. Runs NO device command (per contract): it reads results.json and the
committed evidence only. It verifies that the ordinary-launch FAILURE is recorded completely and that the
b189 HAP was recovered — it does NOT mark the task as passed (the scenario is human-reviewed). Production
negatives drive the real check() to refuse forged success, a fabricated callback, the wrong
"observed_absent" framing, an identity mismatch, an unconfirmed/disk-only recovery, a checker that marks
task pass, a committed screenshot, and a claim that an uncaptured runtime fingerprint was captured.
"""
import argparse, copy, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B189 = 'b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
CAND = '02f56d181fa883f96505e196570eab6ea75911fa2f1e5edab15f5180c9f19485'

class Bad(Exception): ...
def need(c, m):
    if not c: raise Bad(m)

def check(d, evdir):
    # task semantics: a launch failure, not a success
    need(d['status'] == 'OFFLINE_DEVICE_LAUNCH_FAILED_PERMISSION_DENIED_RESTORED', 'status')
    need(d['task_result'].startswith('launch_denied_10107101'), 'task_result')
    need(d['acceptance']['automated_checker_marks_task_pass'] is False, 'checker must not mark task pass')
    need(d['claims']['checker_runs_device_commands'] is False, 'checker runs device commands claim')
    need(d['claims']['white_screen_fixed'] is False and d['claims']['onNewWant_inference'] == 'none', 'white-screen / onNewWant claim')
    need(d['claims']['manual_origin'] == 'unverified' and d['claims']['eligible_for_reentry'] is False, 'manual_origin / reentry')
    need(d['claims']['automated_request_only'] is True and d['claims']['human_tap'] is False, 'automated vs human-tap')
    # callback must be unknown (launch denied => path not reached), never "observed_absent after success"
    need(d['callback_status'] == 'unknown', 'callback_status must be unknown (not observed_absent)')
    # the three ordinary requests: all permission-denied, host never launched, no callback file, shell rc0 != success
    need(len(d['requests']) == 3, 'three requests')
    for r in d['requests']:
        need(r['request_kind'] == 'automated_request', 'request_kind')
        need(r['launch_result'] == 'permission_denied' and r['error_code'] == '10107101', 'launch_result/error_code')
        need(r['host_launched'] is False and r['host_pid'] == 'NONE', 'host must not launch')
        need(r['launch_observation_json'] == 'absent' and r['window_state_changed'] is False, 'no callback file / window change')
        need(r['shell_rc'] == 0, 'shell rc recorded')  # rc0 coexists with failure -> proves rc0 != success
        i = r['index']
        out = (evdir / f'aa_start-req{i}.stdout').read_text()
        need('10107101' in out and 'Permission check' in out and 'failed to start ability' in out, f'req{i} stdout failure text')
        need((evdir / f'aa_start-req{i}.rc').read_text().strip() == '0', f'req{i} shell rc0 evidence')
    # identity before == after restore (public bm-dump fields only)
    need(d['identity_before'] == {k: v for k, v in d['identity_after_restore'].items()}, 'identity before==after')
    need(d['identity_unchanged_before_after'] is True, 'identity_unchanged flag')
    # recovery: b189 on device AND candidate never ran (not disk-only)
    rec = d['recovery']
    need(rec['device_hap_after_restore_sha256'] == B189 and rec['recovery_confirmed'] is True, 'recovery hap / confirmed')
    need('never ran' in rec['candidate_pid'] and 'not disk-only' in rec['recovery_basis'], 'recovery must not be disk-only')
    need(d['device_hap_before_sha256'] == B189 and d['update']['device_hap_after_install_sha256'] == CAND, 'hap before/after update')
    # evidence scope honesty: uncaptured items stay uncaptured (not acceptance)
    nc = d['evidence_scope']['not_captured']
    need('runtime_native_fingerprint' in nc and 'data_dir_inode_and_full_metadata' in nc and 'req1_screenshot' in nc, 'evidence scope not_captured')
    need(d['runtime_fingerprint'] == 'not_captured', 'runtime fingerprint must be not_captured')
    # privacy: no screenshot committed; results only pins sha/private-path/classification
    need(not list(evdir.glob('*.jpeg')) and not list(evdir.glob('*.png')), 'no screenshot may be committed')
    for r in d['requests']:
        sh = r.get('screenshot')
        if sh is not None:
            need(sh['classification'] == 'wlan-settings-page' and sh['private_path'].startswith('$HOME/') and 'sha256' in sh, 'screenshot pin shape')
            need('ssid' not in json.dumps(sh).lower() or 'kept private' in sh.get('note', ''), 'no SSID list in screenshot pin')
    for alias in d['raw_pins']:
        need(alias.startswith('$HOME/') or alias.startswith('/data/') or not alias.startswith('/Users/'), f'raw pin path alias: {alias}')
    return {'verdict': 'FAILURE_RECORDED_AND_RECOVERED', 'task_pass': False,
            'requests_all_permission_denied_10107101': True, 'host_launched': False,
            'callback_status': 'unknown', 'shell_rc0_is_not_success': True,
            'identity_unchanged_public_fields': True, 'recovery_confirmed_b189_candidate_never_ran': True,
            'runtime_fingerprint': 'not_captured', 'data_dir_scope': 'uid_gid_only',
            'screenshot_committed': False, 'device_commands_run_by_checker': 0}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results', type=Path, default=HERE / 'results.json')
    ap.add_argument('--evidence', type=Path, default=HERE / 'evidence')
    a = ap.parse_args()
    data = json.loads(a.results.read_text())
    verdict = check(data, a.evidence)

    def mut(fn):
        d = copy.deepcopy(data); fn(d); return d
    def refuse(name, d, token):
        try: check(d, a.evidence)
        except Bad as e:
            need(token in str(e), f'{name}: wrong refusal {e}'); return {'case': name, 'refused': str(e)}
        raise Bad(f'negative accepted: {name}')
    negs = [
        refuse('forged white-screen fix', mut(lambda d: d['claims'].__setitem__('white_screen_fixed', True)), 'white-screen'),
        refuse('wrong observed_absent framing', mut(lambda d: d.__setitem__('callback_status', 'observed_absent')), 'callback_status'),
        refuse('fabricated callback file', mut(lambda d: d['requests'][0].__setitem__('launch_observation_json', 'present')), 'callback file'),
        refuse('claimed host launched', mut(lambda d: d['requests'][0].__setitem__('host_launched', True)), 'host must not launch'),
        refuse('identity drift', mut(lambda d: d['identity_after_restore'].__setitem__('appId', 'x')), 'identity before==after'),
        refuse('recovery not b189', mut(lambda d: d['recovery'].__setitem__('device_hap_after_restore_sha256', '0' * 64)), 'recovery hap'),
        refuse('disk-only recovery', mut(lambda d: d['recovery'].__setitem__('recovery_basis', 'disk HAP only')), 'disk-only'),
        refuse('checker marks task pass', mut(lambda d: d['acceptance'].__setitem__('automated_checker_marks_task_pass', True)), 'mark task pass'),
        refuse('runtime fingerprint claimed captured', mut(lambda d: d.__setitem__('runtime_fingerprint', 'abc')), 'runtime fingerprint'),
        refuse('shell rc0 reported as nonzero-hidden success', mut(lambda d: d['requests'][0].__setitem__('launch_result', 'ok')), 'launch_result/error_code'),
    ]
    print(json.dumps({**verdict, 'negatives': negs}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
