#!/usr/bin/env python3
"""Every changed artifact in a version's increments.csv must have at least one observer.

    check_fix_observers.py <increments.csv> <keys.json> [--smoke <smoke.json>...] [--csv out.csv]

Observers per artifact (changed file -> who watches it):
  - a mover in the observation keys json whose per_key source names the artifact's owning
    deliverable (matched by the deliverable tokens in the source string: jar names, native
    library basenames, framework/bitmap/m3/nsd/atrace keywords), or
  - a live smoke-spec marker naming the artifact (path substring) — passed as --smoke JSON
    files with a 'markers' / 'checks' list, or a smoke spec with probe expectations.
Artifacts with NO observer are reported as GAP rows; the run exits 1 if any GAP remains.
"""
import argparse, csv, json, re, sys
from pathlib import Path

# deliverable token -> artifact paths it observes (a source string containing the token
# observes every listed path substring)
TOKEN_TO_PATHS = {
    'u15-jar-v1': ['framework.jar', 'adapter-mainline-stubs.jar', 'oh-adapter-runtime.jar',
                   'boot-framework', 'apache-xml.jar', 'bouncycastle.jar', 'core-icu4j.jar',
                   'core-libart.jar', 'okhttp.jar'],
    'u15-framework-bitmap': ['framework.jar', 'boot-framework'],
    'u15-runtime-m3': ['liboh_android_runtime.so', 'appspawn-x', 'boot-framework'],
    'u15-stubs-nsd': ['adapter-mainline-stubs.jar', 'boot-adapter-mainline-stubs'],
    'u15-flutter-libandroid': ['westlake_flutter/libandroid.so'],
    'u14-native-abi-gecko': ['libbionic_compat.so', 'appspawn-x', 'liboh_android_runtime.so'],
    'u14-native-abi-v2': ['libbionic_compat.so', 'appspawn-x'],
    'bt-le-scancallback': ['adapter-mainline-stubs.jar', 'boot-adapter-mainline-stubs'],
    'u14-flutter-libandroid': ['westlake_flutter/libandroid.so'],
    'u14 ICU alias': ['libicui18n', 'libicuuc', 'appspawn-x'],
    'u14-m5-watchlist': ['appspawn-x', 'liboh_android_runtime.so'],
}


BOOT_IMG = re.compile(r'/arm64/boot(?:-([\w.-]+))?\.(?:art|oat|vdex)$')


def sha_hits(target, movers_sources, row_shas):
    """Mover sources naming a SHA prefix that matches this row's candidate/baseline SHA."""
    out = []
    for src in movers_sources:
        for pre in sha_prefixes(src):
            if any(rs.startswith(pre) for rs in row_shas):
                out.append(f'{pre} <- {src[:40]}')
    return out


def jar_of_boot_image(target):
    """Source JAR path for a boot image file (boot-<name>.art/.oat/.vdex <- <name>.jar);
    None for non-image targets. adapter-mainline-stubs -> adapter-mainline-stubs.jar; the
    bare combined image boot.art/.oat maps to the virtual boot.jar (base 'boot')."""
    m = BOOT_IMG.search(target)
    if not m:
        return None
    name = m.group(1) or 'boot'
    return f'/system/android/framework/{name}.jar'


def observers_for(target, movers_sources, smoke_markers, all_targets=(), row_shas=(), smoke_obs=()):
    """Observer strings covering this changed artifact path. A mechanically re-baked boot
    image counts as observed when its source JAR (present in the same increments) is observed
    (reported as derived-from)."""
    hits = []
    base = target.rsplit('/', 1)[-1]
    for token, paths in TOKEN_TO_PATHS.items():
        for p in paths:
            if p in target or (p == base):
                for src in movers_sources:
                    if token in src:
                        hits.append(f'mover[{src[:60]}]')
                for m in smoke_markers:
                    if p in m or p in str(m):
                        hits.append(f'smoke[{str(m)[:40]}]')
    for label, subs, shas in smoke_obs:
        if any(s in target or target.endswith('/' + s) for s in subs):
            hits.append(label)
        for pre in shas:
            if any(rs.startswith(pre) for rs in row_shas if pre in rs or rs.startswith(pre)):
                if any(s in target or target.endswith('/' + s) for s in subs) or not subs:
                    hits.append(label)
                break
    if not hits:
        for pre in sha_hits(target, movers_sources, row_shas):
            hits.append(f'sha[{pre}]')
    if not hits:
        jar = jar_of_boot_image(target)
        if jar:
            jar_obs = observers_for(jar, movers_sources, smoke_markers)
            if jar_obs:
                hits.append(f'derived-from[{jar.rsplit("/", 1)[-1]}]')
            else:
                # boot.art / boot.oat (the combined image): derive from ANY observed BCP jar
                # in the same increments — the combined image is a mechanical re-bake of them all
                jar_base = jar.rsplit('/', 1)[-1][:-4]
                if jar_base == 'boot':
                    for other in sorted(all_targets):
                        oj = jar_of_boot_image(other) or (other if other.endswith('.jar') else None)
                        if oj and oj != jar and observers_for(oj, movers_sources, smoke_markers):
                            hits.append(f'derived-from[{oj.rsplit("/", 1)[-1]} (combined boot image)]')
                            break
    return sorted(set(hits))


SHA_IN_TEXT = re.compile(r'\b[0-9a-f]{6,12}\b')
SHA_COL = re.compile(r'^[0-9a-f]{64}$')


def sha_prefixes(src):
    """Candidate/baseline SHA prefixes (6-12 hex) named in a mover source string."""
    out = set()
    for m in SHA_IN_TEXT.finditer(src):
        tok = m.group(0)
        # skip common english hex-ish words of length 6 that are all letters a-f only rarely;
        # require at least one digit to reduce false hits
        if any(c.isdigit() for c in tok):
            out.add(tok)
    return out


def load_smoke(smoke_paths):
    """smoke proposals -> list of (observer_label, observed_path_substrings, sha_prefixes)."""
    obs = []
    for sp in smoke_paths:
        try:
            d = json.loads(Path(sp).read_text())
        except (OSError, ValueError):
            continue
        label = Path(sp).name
        probe = d.get('probe') or {}
        for path in probe.get('files', {}):
            sha = str(probe['files'][path])
            obs.append((f'smoke[{label}]', [path.rsplit('/', 1)[-1]],
                        sha_prefixes(sha) if SHA_COL.match(sha) else {sha[:12]}))
        for fx in d.get('fixes', []):
            fid = str(fx.get('id', ''))
            # marker ids name their artifact: BRIDGE->liboh_adapter_bridge, RUNTIME->runtime jar,
            # FLUTTER->flutter libandroid, AMB-ORDER->oh-adapter-runtime
            maps = {'BRIDGE': ['liboh_adapter_bridge'], 'RUNTIME': ['oh-adapter-runtime', 'liboh_android_runtime'],
                    'FLUTTER': ['libandroid'], 'AMB-ORDER': ['oh-adapter-runtime']}
            subs = [s for k, v in maps.items() if k in fid for s in v]
            shas = sha_prefixes(fid + ' ' + str(fx.get('source', '')))
            if subs or shas:
                obs.append((f'smoke[{label}#{fid}]', subs, shas))
    return obs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('increments', type=Path)
    ap.add_argument('keys', type=Path)
    ap.add_argument('--smoke', type=Path, nargs='*', default=[])
    ap.add_argument('--csv', type=Path)
    a = ap.parse_args(argv)

    inc = list(csv.DictReader(a.increments.open()))
    doc = json.loads(a.keys.read_text())
    movers_sources = []
    for b in doc.get('boards', []):
        for sh in b.get('shards', []):
            if 'movers' in sh.get('name', ''):
                for k, v in (sh.get('per_key') or {}).items():
                    movers_sources.append(v['source'] if isinstance(v, dict) else str(v))
    smoke_obs = load_smoke(a.smoke)
    smoke_markers = [label for label, _, _ in smoke_obs]

    all_targets = {r['target'] for r in inc}
    rows, gaps = [], []
    for r in inc:
        t = r['target']
        row_shas = tuple(s for s in (r.get('baseline_sha256'), r.get('candidate_sha256')) if s)
        obs = observers_for(t, movers_sources, smoke_markers, all_targets, row_shas, smoke_obs)
        row = {'variant': r['variant'], 'layer': r['layer'], 'target': t,
               'observers': '; '.join(obs) if obs else '', 'status': 'OK' if obs else 'GAP'}
        rows.append(row)
        if not obs:
            gaps.append(t)
    for r in rows:
        print(f"{r['status']:4s} {r['variant']:7s} {r['layer']:6s} {r['target']}  {r['observers'][:80]}")
    print(f"{len(rows)} artifacts, {len(gaps)} without an observer")
    if a.csv:
        with a.csv.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['variant', 'layer', 'target', 'observers', 'status'])
            w.writeheader()
            w.writerows(rows)
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main())
