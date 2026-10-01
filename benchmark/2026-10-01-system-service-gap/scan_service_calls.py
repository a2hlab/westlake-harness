#!/usr/bin/env python3
"""Which Context system services each U9 key actually asks for, counted at getSystemService call sites.

For every classes*.dex of every APK of a key, `dexdump -d` the code and look 6 instructions back from each
`getSystemService(String)` / `getSystemService(Class)` invoke (any receiver: Context, Activity, Application,
ContextWrapper, ContextCompat, app subclasses). A const-string in that window counts only when it equals an
AOSP 14 Context.*_SERVICE value; a const-class counts when SystemServiceRegistry registers it under a Context
constant. A string merely present in the dex string pool is not a request (the first scan counted "text" and
"log" in 160 keys that way).

    scan_service_calls.py [--keys k1,k2] [--jobs N]
writes requested-services.csv (key,service,call_sites,form,u9_verdict,source) and service-summary.csv
(service,keys,lit,not_lit,call_sites) next to this script.
"""
import argparse
import collections
import concurrent.futures
import csv
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

AOSP = lab_paths.inputs() / 'aosp-14.0.0_r1-src/frameworks/base/core/java/android'
SIGNOFF = REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json'
ROOTS = {'original-66': Path.home() / 'a2hlab/app-inputs', 'cv2-100': lab_paths.inputs() / 'corpus-v2/app-inputs'}
DEXDUMP = sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/dexdump'))[0]
CALL = re.compile(r'\.getSystemService:\((?:Landroid/content/Context;)?Ljava/lang/(?:String|Class);\)')
CONST_STRING = re.compile(r'const-string(?:/jumbo)? v\d+, "([^"]*)"')
CONST_CLASS = re.compile(r'const-class v\d+, (L[^;]+;)')
WINDOW = 6


def context_services():
    src = (AOSP / 'content/Context.java').read_text()
    consts = dict(re.findall(r'public static final String ([A-Z0-9_]+_SERVICE)\s*=\s*"([^"]+)"', src))
    return consts, set(consts.values())


def class_map(consts):
    src = (AOSP / 'app/SystemServiceRegistry.java').read_text()
    imports = {m.split('.')[-1]: m for m in re.findall(r'^import ([\w.]+);', src, re.M)}
    out = {}
    for const, cls in re.findall(r'registerService\(\s*Context\.([A-Z0-9_]+)\s*,\s*([\w.]+)\.class', src):
        if const not in consts:
            continue
        fq = cls if '.' in cls and cls[0].islower() else imports.get(cls.split('.')[0], cls)
        if '.' in cls and cls[0].isupper():   # nested class, e.g. Foo.Bar
            fq = imports.get(cls.split('.')[0], cls.split('.')[0]) + '$' + cls.split('.', 1)[1].replace('.', '$')
        out['L' + fq.replace('.', '/') + ';'] = consts[const]
    return out


def deployed_class_map(names):
    """Class -> service name from the deployed boot framework.jar's own register*Service calls.

    SystemServiceRegistry.java alone misses the apex FrameworkInitializer registrations (TelephonyManager -> phone,
    SubscriptionManager, CarrierConfigManager, ...), so getSystemService(TelephonyManager.class) went uncounted
    (2026-10-01 22:3x, found while sorting the U11 JAR clusters). The route-A framework.jar is byte-identical across
    generations (3e106350), so any generation's copy is the deployed one."""
    jars = sorted(lab_paths.workspaces().glob('westlake-generation-*/payload/android/framework/framework.jar'))
    if not jars:
        return {}
    out = {}
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(jars[0]) as z:
        for n in [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]:
            path = Path(tmp) / n
            path.write_bytes(z.read(n))
            lines = subprocess.run([str(DEXDUMP), '-d', str(path)], capture_output=True, text=True,
                                   errors='replace', timeout=300).stdout.splitlines()
            for i, line in enumerate(lines):
                if 'invoke-static' not in line or 'Landroid/app/SystemServiceRegistry;.register' not in line:
                    continue
                name = cls = None
                for prev in reversed(lines[max(0, i - 10):i]):
                    name = name or (m.group(1) if (m := CONST_STRING.search(prev)) else None)
                    cls = cls or (m.group(1) if (m := CONST_CLASS.search(prev)) else None)
                if name in names and cls:
                    out[cls] = name
    return out


def apks(key):
    for source, root in ROOTS.items():
        d = root / key
        if d.is_dir():
            found = sorted(d.glob('*.apk'))
            if found:
                return source, found
    return None, []


def scan(key, names, classes):
    source, files = apks(key)
    if not files:
        return key, source, None, 'no APK'
    counts = collections.Counter()
    with tempfile.TemporaryDirectory() as tmp:
        for apk in files:
            with zipfile.ZipFile(apk) as z:
                dexes = [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]
                for n in dexes:
                    path = Path(tmp) / f'{apk.stem}-{n}'
                    path.write_bytes(z.read(n))
                    r = subprocess.run([str(DEXDUMP), '-d', str(path)], capture_output=True, text=True,
                                       errors='replace', timeout=300)
                    if r.returncode:
                        return key, source, None, f'dexdump rc={r.returncode} on {apk.name}:{n}'
                    lines = r.stdout.splitlines()
                    for i, line in enumerate(lines):
                        if not CALL.search(line):
                            continue
                        for prev in reversed(lines[max(0, i - WINDOW):i]):
                            m = CONST_STRING.search(prev)
                            if m and m.group(1) in names:
                                counts[(m.group(1), 'name')] += 1
                                break
                            m = CONST_CLASS.search(prev)
                            if m and m.group(1) in classes:
                                counts[(classes[m.group(1)], 'class')] += 1
                                break
                    path.unlink()
    return key, source, counts, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--keys')
    ap.add_argument('--jobs', type=int, default=4)
    args = ap.parse_args()
    consts, names = context_services()
    classes = class_map(consts)
    classes = {**deployed_class_map(names), **classes}
    signoff = json.loads(SIGNOFF.read_text())['keys']
    keys = args.keys.split(',') if args.keys else sorted(signoff)
    rows, errors = [], {}
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for key, source, counts, err in pool.map(lambda k: scan(k, names, classes), keys):
            if err:
                errors[key] = err
                continue
            verdict = signoff.get(key, {}).get('verdict', 'unknown')
            for (svc, form), n in sorted(counts.items()):
                rows.append({'key': key, 'service': svc, 'call_sites': n, 'form': form,
                             'u9_verdict': verdict, 'source': source})
            print(f'{key}: {len({s for s, _ in counts})} services, {sum(counts.values())} call sites', flush=True)
    rows.sort(key=lambda r: (r['key'], r['service'], r['form']))
    with open(HERE / 'requested-services.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    per = collections.defaultdict(lambda: {'keys': set(), 'lit': set(), 'call_sites': 0})
    for r in rows:
        p = per[r['service']]
        p['keys'].add(r['key'])
        p['call_sites'] += r['call_sites']
        if r['u9_verdict'] == 'lit':
            p['lit'].add(r['key'])
    with open(HERE / 'service-summary.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['service', 'keys', 'lit', 'not_lit', 'call_sites'])
        for svc, p in sorted(per.items(), key=lambda kv: (-len(kv[1]['keys']), kv[0])):
            w.writerow([svc, len(p['keys']), len(p['lit']), len(p['keys']) - len(p['lit']), p['call_sites']])
    print(f'{len(keys)} keys asked, {len(keys) - len(errors)} scanned, {len(per)} services, '
          f'{len(classes)} registry classes mapped')
    for k, e in sorted(errors.items()):
        print(f'ERROR {k}: {e}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
