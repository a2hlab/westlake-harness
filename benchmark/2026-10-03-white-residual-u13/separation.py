#!/usr/bin/env python3
"""Separation table from features.json: for each white mechanism condition, how many residual keys and how many
latest-lit keys (U13 windows 1-2, outer-signed lit) carry it. A condition explains white only if the lit keys lack it.

    separation.py  -> separation.json (and a printed table)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COND = ['M1_misroute', 'M2_webview_full', 'M3_gl_iae', 'M4_no_session', 'M5_dialog_before_main', 'M6_top_dropped',
        'surface_full', 'webview_proxy_marker']


def main():
    rows = json.loads((HERE / 'features.json').read_text())
    res = [r for r in rows if r['population'] == 'residual']
    lit = [r for r in rows if r['population'] == 'lit']
    lit_keys = sorted({r['key'] for r in lit})
    out = {'residual_keys': len(res), 'lit_keys': len(lit_keys), 'lit_runs': len(lit), 'conditions': {}}
    for c in COND:
        rk = sorted(r['key'] for r in res if r.get(c))
        lk = sorted({r['key'] for r in lit if r.get(c)})
        out['conditions'][c] = {'residual': rk, 'lit_keys': lk, 'lit_runs': sum(bool(r.get(c)) for r in lit)}
        print(f'{c:24s} residual {len(rk)}/{len(res)}  lit {len(lk)}/{len(lit_keys)} keys '
              f'({out["conditions"][c]["lit_runs"]}/{len(lit)} runs)')
    (HERE / 'separation.json').write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
