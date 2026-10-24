#!/usr/bin/env python3
"""Offline T131 receipt inventory. Never executes recorded argv or contacts a device."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs, pins = [], []
    for run in sorted((ROOT / '.private').glob('run-*')):
        facts = json.loads((run / 'facts.json').read_text())
        receipts = {}
        for p in sorted(run.glob('*/receipt.json')):
            r = json.loads(p.read_text())
            for stream in ('stdout', 'stderr'):
                assert sha(p.parent / stream) == r[stream + '_sha256']
            receipts[p.parent.name] = r
        images = []
        for item in facts['images']:
            path = run / Path(item['path']).name
            assert sha(path) == item['sha256']
            images.append({k: item[k] for k in ('label', 'sha256', 'received_monotonic')})
        def count(label):
            r = receipts.get(label)
            return int(r is not None and r['local_rc'] == 0)
        identities = []
        for p in sorted(run.glob('identity-*/stdout')):
            lines = p.read_text().splitlines()
            processes = []
            for i, line in enumerate(lines):
                if line.startswith('PROC:'):
                    _, pid, parent, uid, name = line.split(':', 4)
                    stat = lines[i + 1].rsplit(')', 1)[1].split()
                    processes.append(dict(pid=int(pid), parent=int(parent), uid=int(uid), name=name, birth_ticks=int(stat[19])))
            identities.append(dict(receipt=p.parent.name, processes=processes))
        final = receipts['final-held']
        released = final['local_rc'] == 1 and not (run / 'final-held/stdout').read_bytes().strip() and not (run / 'final-held/stderr').read_bytes().strip()
        assert released == facts['released']
        runs.append(dict(run=run.name, boot=facts['boot'], images=images,
                         screenshots_received=len(images), samples=len(facts['samples']),
                         wake=count('wake'), swipe=count('unlock-swipe'), home=count('home'), click=count('click-once'),
                         outcome=facts['outcome'], error=facts.get('error'), identities=identities,
                         released=released, final_held_rc=final['local_rc'], ended_utc=final['end_utc'],
                         power_preimage=facts.get('power_preimage'), power_final=facts.get('power_final'),
                         power_restored=facts.get('power_restored'),
                         command_count=len(receipts)))
        for p in sorted(run.rglob('*')):
            if p.is_file():
                pins.append(dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=sha(p)))
    totals = {k: sum(r[k] for r in runs) for k in ('screenshots_received', 'samples', 'wake', 'swipe', 'home', 'click', 'command_count')}
    results = dict(task='T131', status='partially_unverified', run_count=len(runs),
                   original_deadline='2026-10-25T01:41:03+08:00', original_t0_monotonic=2403383.485307541,
                   totals=totals, runs=runs, foreground_event_observed='unknown_no_record_samples',
                   foreground_persistence_seconds=None, child_read_proven=False, runtime_changed=False,
                   limitation='No target click, no window-state samples; no claim about foreground publication or app recovery.',
                   recorder_defect='Override set only before uitest; no immediate setting readback or post-uitest effective override verification.',
                   override_reset_proven=False,
                   next_order='Within a separately authorized budget: save power preimage; after every uitest operation read effective override, reapply the authorized temporary override if reset and verify both fields; take and review fresh screenshot/layout before any click; finally restore and verify original fields.')
    (ROOT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    (ROOT / 'raw-index.json').write_text(json.dumps(dict(private=True, files=pins), indent=2) + '\n')
    text = '\n'.join(f'{k}={v}' for k, v in dict(runs=len(runs), **totals, released_runs=sum(r['released'] for r in runs)).items()) + '\n'
    (ROOT / 'facts.txt').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
