#!/usr/bin/env python3
"""Merge per-key.json (compare.py) with the window-3/4 pair sheets and the readings below into table.md / table.csv.

    table.py

Screens column, in order of authority:
  outer      outer sign-off (window1-3 outer-signoff.json, window-4 board ACK for fd-client)
  pair auto  scripts/lab/pair_sheet.py pre-screen vs the U10.1T8 reference (same/different/no-window), unsigned
  cc-t3 read cc-t3's look at the window-4 suspect tiles (pair-w4/tiles-suspects), UNSIGNED -- for the outer to confirm
Notes column: attribution of moves the prediction table did not expect, and why some moves are not U12's.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

READ = {  # cc-t3, unsigned, from pair-w4/tiles-suspects/*-WIN-*.jpeg
    'cv2-com-kaajjo-libresudoku': 'own UI (LibreSudoku start screen: board + 开始 + settings)',
    'cv2-com-trianguloy-clipboardeditor': 'own UI (clipboard editor panel, top-left, on white)',
    'cv2-com-nbossard-packlist': 'own UI (empty trip list, title = class name: labelRes wall)',
    'cv2-com-nononsenseapps-notepad': 'own UI (task list "欢迎! 打开这个即可开始")',
    'fd-uhabits': 'own UI (Loop welcome page) -- lottery key, not a U12 move',
    'x': 'white (no window)',
    'toutiao': 'desktop (process gone); U10.1T8 reference: white',
}
NOTES = {
    'fd-im-vector-app': 'unpredicted, U12-attributable: U12 private libz alias fixed "libz.so not found" for librealm-jni; next wall UNSUPPORTED-SYMBOL in the same dlopen (same mechanism as mcdonalds)',
    'mcdonalds': 'unpredicted, U12-attributable: terminal unchanged (DI NPE = consequence); the wall under it moved libz -> _ctype_ UNSUPPORTED-SYMBOL (outer: libz->_ctype_)',
    'toutiao': 'NOT attributable to U12: new wall NoSuchMethodError NetworkInfo.getSubtype in CronetInit; NetworkInfo is identical in stubs 2f365a75 and 615b8bbe (no getSubtype in either) and no U12 change touches it; the U10.1T8 reference run is from the toutiao-gain shard -> run variance',
    'cv2-com-lcdcode-moodcairns': 'moved INTO OUR FIX: IllegalStateException "GCM cipher needs to be initialised" at adapter.core.GcmDefaultNonce$Spi.engineDoFinal -- see README (GcmDefaultNonce defect)',
    'fd-wifianalyzer': 'moved to next wall: NoSuchMethodError WifiManager.isScanThrottleEnabled()',
    'fd-breezyweather': 'moved to next wall: lateinit property weatherView has not been initialized (app-level, after the ICU fix)',
    'x': 'moved to next wall: NPE ITelephonyRegistry.listenWithEventList (fixed in U13 JAR v2 506abe23)',
    'burgerking': 'moved: libNitroMmkv dlopen (libz) gone; now SIGSEGV in librsa_bridge (Go cgo x_cgo_sigaction) on pool-4-thread-1',
    'cv2-com-kaajjo-libresudoku': 'moved: no termination, alive at t20',
}


def pair_auto():
    out = {}
    for w in ('w3', 'w4'):
        f = HERE / f'pair-{w}/pair-sheet.json'
        if f.exists():
            for p in json.loads(f.read_text()).get('pairs', []):
                out.setdefault(p['key'], []).append(f"{w}:{p.get('auto')}")
    return out


def main():
    rows = json.loads((HERE / 'per-key.json').read_text())
    auto = pair_auto()
    out = []
    for r in rows:
        u12 = ' || '.join(sorted({f"{x['kind']}: {x['cause'][:110]}" for x in r['u12_runs']}))
        u12w = ' || '.join(sorted({x['wall'][:110] for x in r['u12_runs'] if x['wall']}))
        outer = '; '.join(s for s in r['screens'] if 'unsigned' not in s)
        out.append({'key': r['key'], 'predicted': r['predicted_mover'], 'predicted_by': r['predicted_by'],
                    'actual': r['actual'], 'moved_by': r['moved_by'],
                    'u10_1t8': f"{r['u10_1t8_kind']}: {r['u10_1t8_cause'][:110]}", 'u10_1t8_wall': r['u10_1t8_wall'][:110],
                    'u12': u12, 'u12_wall': u12w,
                    'windows': ' '.join(f"{x['window']}/{x['board']}" for x in r['u12_runs']),
                    'screen_outer': outer or '-', 'screen_pair_auto': ' '.join(auto.get(r['key'], [])) or '-',
                    'screen_cc_t3_unsigned': READ.get(r['key'], ''), 'notes': NOTES.get(r['key'], '')})
    with open(HERE / 'table.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    order = {'moved': 0, 'same': 1, 'not-run': 2}
    lines = ['| key | predicted (by) | actual | U10.1T8 first fatal → U12 first fatal | screen: outer / pair-auto / cc-t3 read (unsigned) | notes |',
             '|---|---|---|---|---|---|']
    for r in sorted(out, key=lambda r: (r['predicted'] != 'yes', order[r['actual']], r['key'])):
        ff = r['u10_1t8'] if r['actual'] == 'same' else f"{r['u10_1t8']} → {r['u12']}"
        if r['moved_by'] and 'wall' in r['moved_by'] and r['u12_wall']:
            ff += f" (wall: {r['u12_wall']})"
        scr = ' / '.join(x for x in (r['screen_outer'], r['screen_pair_auto'], r['screen_cc_t3_unsigned']) if x)
        lines.append(f"| {r['key']} | {r['predicted']} ({r['predicted_by'] or '-'}) | **{r['actual']}** {r['moved_by']} | "
                     f"{ff.replace('|', '/')} | {scr.replace('|', '/')} | {r['notes'].replace('|', '/')} |")
    (HERE / 'table.md').write_text('\n'.join(lines) + '\n')
    print(len(out), 'rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
