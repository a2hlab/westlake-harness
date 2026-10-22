#!/usr/bin/env python3
"""T44 receipt-structure checker (no device commands). Validates results.json invariants, optionally re-hashes the
private raw root when present, and drives check() against forged variants that must be refused."""
import argparse, copy, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
B189 = 'b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
CAND = '02f56d181fa883f96505e196570eab6ea75911fa2f1e5edab15f5180c9f19485'
NODE = 'AppIconCommonView_org.westlake.imehost.EntryAbility'


def check(r):
    p = []
    a = r['admission']
    if a['hap_sha256'] != B189: p.append('admission HAP is not b189')
    if r['lock']['held_seconds'] > 1800: p.append('lock exceeded 20+10 minutes')
    if 'none' not in r['lock']['holder_after_unlock']: p.append('lock still held')
    pre = r['preimage']
    if pre['runtime_missing'] or pre['boot_image_missing']: p.append('preimage has MISSING files')
    if 'OverrideTimeout' not in pre['power']: p.append('power preimage lacks OverrideTimeout')
    d = r['desktop_b189']
    if d['first_valid']['lock_ids'] or not d['first_valid']['workspace']: p.append('first desktop not valid')
    sw = d['page_swipes']
    if sw['next_used'] > 9 or sw['prev_used'] > 9 or sw['next_used'] + sw['prev_used'] > 18: p.append('swipe budget exceeded')
    if len(set(sw['pages'])) != len(sw['pages']): p.append('repeated page counted as traversal')
    t = d['target']
    if t['node'] != NODE or not (t['unique'] and t['actionable']) or t['clicked_before_install']: p.append('b189 target not located properly')
    if r['unlock_swipes_used'] > 2 or r['credential_prompt']: p.append('lock-screen handling out of bounds')
    i = r['install']
    if i['candidate_sha256'] != CAND or i['device_hap_after'] != CAND or i['candidate_bytes'] != 59008: p.append('candidate identity mismatch')
    c = r['clicks']
    if len(c) != 2: p.append('expected exactly two clicks')
    for k in c:
        if k['label'] != 'automated_desktop_click': p.append('click mislabeled')
        if not k['located_in']['actionable'] or not k['located_in']['workspace']: p.append('click without fresh valid location')
    if len(c) == 2:
        o1 = c[0]['post']['launch-observation.json'].get('content') or {}
        o2 = c[1]['post']['launch-observation.json'].get('content') or {}
        if c[0]['pre']['launch-observation.json']['present']: p.append('click1 pre-existing observation not handled')
        if not (o2.get('sequence', 0) > o1.get('sequence', 0) and c[1]['post']['launch-observation.json']['sha256'] != c[1]['pre']['launch-observation.json']['sha256']):
            p.append('click2 callback not a new record')
        for o in (o1, o2):
            if o.get('manual_origin') != 'unverified' or o.get('eligible_for_reentry') is not False: p.append('observation claims authority')
    cb = r['callbacks']
    if cb['manual_origin'] != 'unverified' or cb['eligible_for_reentry'] is not False: p.append('callbacks grant authority')
    rc = r['recovery']
    if rc['device_hap_after'] != B189 or rc['b189_sent_sha256'] != B189: p.append('b189 not restored')
    for k in ('runtime_manifest_identical', 'boot_image_manifest_identical', 'datadir_stat_identical', 'boot_id_same', 'bundle_identity_unchanged'):
        if rc[k] is not True: p.append('recovery not verified: ' + k)
    if rc['power_final'].split(':', 1)[1].split() != pre['power'].split(':', 1)[1].split(): p.append('power not restored to preimage')
    if not rc['candidate_host_running_after'].startswith('no'): p.append('candidate host still running')
    if r['task_pass'] is True: p.append('task_pass must stay pending human review')
    if any('white-screen fix' == x for x in r.get('claimed', [])): p.append('white-screen fix claimed')
    return p


def raw_check(r, require_raw=False):
    root = Path.home() / '.local/share/westlake/t44-verified-desktop-observation-20261022'
    if not root.is_dir():
        if require_raw: raise RuntimeError('original raw root required')
        return 'raw root absent on this host: skipped'
    m = root / 'MANIFEST.sha256'
    if hashlib.sha256(m.read_bytes()).hexdigest() != r['raw_manifest_sha256']: raise RuntimeError('raw manifest SHA drift')
    bad = []
    lines = m.read_text().splitlines()
    names = [line.split(None, 1)[1] for line in lines]
    if len(names) != r['raw_manifest_files'] or len(names) != len(set(names)): raise RuntimeError('raw manifest count mismatch')
    if any(Path(n).is_absolute() or ".." in Path(n).parts for n in names): raise RuntimeError('unsafe raw manifest path')
    for line in lines:
        h, f = line.split(None, 1)
        if hashlib.sha256((root / f).read_bytes()).hexdigest() != h: bad.append(f)
    if bad: raise RuntimeError('raw files drift: %s' % bad[:5])
    return 'raw root verified: %d files' % len(m.read_text().splitlines())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-raw', action='store_true')
    args = ap.parse_args()
    r = json.loads((HERE / 'results.json').read_text())
    probs = check(r)
    if probs: raise RuntimeError(probs)
    print(raw_check(r, args.require_raw))
    forged = []
    def f(fn):
        x = copy.deepcopy(r); fn(x); forged.append(x)
    f(lambda x: x.__setitem__('task_pass', True))
    f(lambda x: x['clicks'].append(copy.deepcopy(x['clicks'][0])))
    f(lambda x: x['desktop_b189']['page_swipes'].__setitem__('next_used', 10))
    f(lambda x: x['desktop_b189']['page_swipes']['pages'].append(x['desktop_b189']['page_swipes']['pages'][-1]))
    f(lambda x: x['recovery'].__setitem__('device_hap_after', CAND))
    f(lambda x: x['recovery'].__setitem__('power_final', 'ScreenOffTime: Timeout=10000ms  OverrideTimeout=600000ms'))
    f(lambda x: x['clicks'][1]['post']['launch-observation.json'].__setitem__('sha256', x['clicks'][1]['pre']['launch-observation.json']['sha256']))
    f(lambda x: x['callbacks'].__setitem__('eligible_for_reentry', True))
    f(lambda x: x['lock'].__setitem__('held_seconds', 1900))
    f(lambda x: x['desktop_b189']['target'].__setitem__('clicked_before_install', True))
    f(lambda x: x['recovery'].__setitem__('runtime_manifest_identical', 'unknown'))
    for i, x in enumerate(forged):
        if not check(x): raise RuntimeError('forged variant %d accepted' % i)
    print('T44 receipt structure OK; %d forged variants refused; task_pass=%s' % (len(forged), r['task_pass']))


if __name__ == '__main__':
    main()
