#!/usr/bin/env python3
"""Offline, sanitized T132 receipt analysis. No recorded commands are executed."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text())


def identities(text):
    lines = text.splitlines()
    result = []
    for i, line in enumerate(lines):
        if line.startswith('PROC:'):
            _, pid, parent, uid, name = line.split(':', 4)
            stat = lines[i + 1].rsplit(')', 1)[1].split()
            result.append(dict(pid=int(pid), parent=int(parent), uid=int(uid), name=name, birth_ticks=int(stat[19])))
    return result


def main():
    runs, pins = [], []
    for run in sorted((ROOT / '.private').glob('run-*')):
        f = load(run / 'facts.json')
        receipts = {p.parent.name: load(p) for p in run.glob('*/receipt.json')}
        for label, rec in receipts.items():
            for stream in ('stdout', 'stderr'):
                assert sha(run / label / stream) == rec[stream + '_sha256']
        def count(label):
            p = run / label
            return int(label in receipts and receipts[label]['local_rc'] == 0 and not (p / 'stderr').read_bytes().strip()
                       and not any(x in (p / 'stdout').read_text(errors='replace') for x in ('[Fail]', 'Connect server failed', 'Permission denied')))
        images = []
        for i in f['images']:
            p = run / Path(i['path']).name
            assert sha(p) == i['sha256']
            images.append(dict(label=i['label'], path=str(p.relative_to(ROOT)), sha256=sha(p), received_monotonic=i['received_monotonic']))
        samples = []
        click = receipts.get('click-once')
        for s in f['samples']:
            d = run / s['label']
            rec = load(d / 'receipt.json')
            text = (d / 'stdout').read_text()
            raw = bytes.fromhex(text.split('HEX_BEGIN\n', 1)[1].split('\nHEX_END', 1)[0])
            assert raw == (d / 'record.bin').read_bytes() and sha(d / 'record.bin') == s['record_sha256']
            x = json.loads(raw)
            stat_before = text.split('RECORD_STAT_BEFORE\n', 1)[1].splitlines()[0]
            stat_after = text.split('RECORD_STAT_AFTER\n', 1)[1].splitlines()[0]
            boot_before = text.splitlines()[1]
            boot_after = text.split('BOOT_AFTER\n', 1)[1].strip()
            assert boot_before == boot_after == f['boot']
            stage = x.get('details', {}).get('event') if x.get('event') == 'stage-event' else None
            samples.append(dict(label=s['label'], path=str((d / 'stdout').relative_to(ROOT)),
                                start_monotonic=rec['start_monotonic'], end_monotonic=rec['end_monotonic'],
                                relative_to_click_start_s=rec['start_monotonic'] - click['start_monotonic'],
                                relative_to_click_return_s=rec['start_monotonic'] - click['end_monotonic'],
                                record_bytes=len(raw), sha256=sha(d / 'record.bin'), event=x.get('event'), stage=stage,
                                window_id=x.get('details', {}).get('window', {}).get('id'), record_time_raw=x.get('time'),
                                foreground_category=x.get('event') == 'window-ready' or stage in (1, 2),
                                stat_before=stat_before, stat_after=stat_after, stat_stable=stat_before == stat_after,
                                boot=boot_before, uptime_raw=text.split('UPTIME\n', 1)[1].splitlines()[0],
                                identities=identities(text)))
        samples.sort(key=lambda s: s['start_monotonic'])
        final = receipts['final-held']
        released = final['local_rc'] == 1 and not (run / 'final-held/stdout').read_bytes().strip() and not (run / 'final-held/stderr').read_bytes().strip()
        power_reads = []
        for label, rec in sorted(receipts.items(), key=lambda kv: kv[1]['start_monotonic']):
            text = (run / label / 'stdout').read_text(errors='replace')
            base = re.search(r'ScreenOffTime: Timeout=(\d+)ms', text)
            state = re.search(r'Current State: (\w+)', text)
            override = re.search(r'OverrideTimeout=(\d+)ms', text)
            if base and state:
                power_reads.append(dict(receipt=label, start_monotonic=rec['start_monotonic'], state=state.group(1), base=int(base.group(1)), override=int(override.group(1)) if override else None))
        runs.append(dict(run=run.name, original_t0_monotonic=f['original_t0_monotonic'],
                         source=load(run / 'source.json')['sha256'], boot=f['boot'],
                         outcome=f['outcome'], error=f.get('error'),
                         screenshots_received=len(images), sample_count=len(samples), images=images, samples=samples,
                         wake=count('wake'), swipe=count('unlock-swipe'), home=count('home'), click=count('click-once'),
                         recorded_swipe_count=f['unlock_swipe_count'],
                         click_receipt={k: click[k] for k in ('start_utc', 'end_utc', 'start_monotonic', 'end_monotonic', 'local_rc')} if click else None,
                         power_preimage=f['power_preimage'], power_final=f['power_final'], power_restored=f['power_restored'],
                         power_reads=power_reads,
                         released=released, final_held_rc=final['local_rc'], ended_utc=final['end_utc'],
                         command_count=len(receipts)))
    for p in sorted((ROOT / '.private').rglob('*')):
        if p.is_file():
            pins.append(dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=sha(p)))
    totals = {k: sum(r[k] for r in runs) for k in ('screenshots_received', 'sample_count', 'wake', 'swipe', 'home', 'click', 'command_count')}
    clicked = [r for r in runs if r['click']]
    assert len(clicked) == 1
    samples = clicked[0]['samples']
    post = [s for s in samples if s['label'] != 'pre-click']
    foreground = [s for s in post if s['foreground_category']]
    result = dict(task='T132', status='ordinary_observation_completed_not_repair', totals=totals, runs=runs,
                  foreground_sample_count=len(foreground), post_click_sample_count=len(post),
                  foreground_first_start_relative_s=foreground[0]['relative_to_click_start_s'] if foreground else None,
                  foreground_last_start_relative_s=foreground[-1]['relative_to_click_start_s'] if foreground else None,
                  foreground_sample_span_s=foreground[-1]['start_monotonic'] - foreground[0]['start_monotonic'] if foreground else None,
                  max_post_sample_start_gap_s=max(b['start_monotonic'] - a['start_monotonic'] for a, b in zip(post, post[1:])),
                  fine_sample_max_start_gap_s=max(b['start_monotonic'] - a['start_monotonic'] for a, b in zip(post[:15], post[1:16])),
                  continuous_persistence_proven=False, child_read_proven=False, runtime_modified=False,
                  limitations=['Root reads only; no proof of child read or record consumption.',
                               'Snapshots are periodic, not an event stream; missing intermediate events cannot be inferred absent.',
                               'First sample follows the synchronous click and its power readbacks; nominal sample-0 is not click time.',
                               'Two sequential lock holds share the original T132 deadline, separated by a stopped parser revision.',
                               'UI visual conclusions require actual screenshot inspection; no parser-based feed assertion.'])
    (ROOT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'raw-index.json').write_text(json.dumps(dict(files=pins, raw_private=True), indent=2) + '\n')
    facts = '\n'.join(f'{k}={v}' for k, v in dict(runs=len(runs), **totals, released_runs=sum(r['released'] for r in runs)).items()) + '\n'
    (ROOT / 'facts.txt').write_text(facts)
    print(facts, end='')


if __name__ == '__main__':
    main()
