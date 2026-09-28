"""Sequential per-board driver; an interrupted attempt stops all remaining writes."""
import json
import t0_collect as c


def run(keys, run_id, base, notify=lambda n, key, state: None, before=lambda key: None):
    status = {key: 'not-run' for key in keys}
    c.save(base / 'shard.json', status)
    for n, key in enumerate(keys, 1):
        before(key)
        code = c.collect(key, run_id)
        row = json.loads((base / key / 'triage.json').read_text())
        status[key] = row['status']
        c.save(base / 'shard.json', status)
        notify(n, key, row['status'])
        if code:
            return code
    return 0
