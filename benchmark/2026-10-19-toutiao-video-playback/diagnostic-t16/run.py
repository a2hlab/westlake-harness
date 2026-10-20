#!/usr/bin/env python3
"""T16 outer-facing entry. DEFAULT = preview (device_calls=0). --execute validates the 5cd fresh-profile
admission then delegates to the reused R13 Session (inside the pinned SDK15 host). This file performs no
device I/O itself; the outer owns hdc port-forward + on-device lldb-server start, then re-invokes with
--port. Raw stdout/stderr + events are written by the reused R13 Session under --out."""
import argparse, json, sys, time
from pathlib import Path
import t16_core


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--admission', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--r13', type=Path, help='pinned diagnostic-r13 dir (reuse base)')
    ap.add_argument('--port', type=int, help='forwarded gdb-remote port (outer has started server+forward)')
    a = ap.parse_args(argv)

    if not a.execute:
        print(json.dumps(t16_core.plan_preview(), indent=2))
        return 0

    # execute: validate the fresh-profile admission offline BEFORE any device delegation
    if not (a.admission and a.out and a.r13):
        sys.stderr.write('execute requires --admission --out --r13 (and --port once the outer has forwarded)\n')
        return 3
    a.out.mkdir(parents=True, exist_ok=False)
    admission = json.loads(a.admission.read_text())
    try:
        t16_core.t16_validate(admission)
    except t16_core.Refuse as e:
        (a.out / 'result.json').write_text(json.dumps({'status': 'ADMISSION_REFUSED', 'reason': str(e)}, indent=2) + '\n')
        sys.stderr.write('ADMISSION_REFUSED: %s\n' % e)
        return 2
    (a.out / 'admission.validated.json').write_text(json.dumps({'validated': True, 'at': time.time()}, indent=2) + '\n')

    if a.port is None:
        # Admission is valid; hand control to the outer to start server + forward, then re-invoke with --port.
        (a.out / 'result.json').write_text(json.dumps({'status': 'ADMISSION_VALID_AWAIT_PORT',
                                                       'next': 'outer: start NDK r23b server 13c0b4bf on device, hdc forward, re-run with --port'}, indent=2) + '\n')
        print(json.dumps({'status': 'ADMISSION_VALID_AWAIT_PORT'}))
        return 0

    # port present: run inside the SDK15 host python (lldb importable). Reuses R13 Session device glue.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import t16_observer
    result = t16_observer.entry(str(a.admission), str(a.out), a.port, str(a.r13))
    print(json.dumps({'status': result.get('status'), 'cleanup_verified': result['cleanup'].get('verified')}))
    return 0 if result.get('status') == 'OBSERVATION_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
