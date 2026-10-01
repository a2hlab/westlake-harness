#!/usr/bin/env python3
"""Compare the dynamic ABI of a rebuilt library against the deployed one: exports AND call signatures.

    abi_diff.py --old <deployed.so> --new <rebuilt.so> [--consumer <lib.so> ...] [--json out.json]

Why (user rule 2026-10-01): a rebuild was accepted on an export-table diff ("14 missing exports, no consumers") and
on the board every app died — OHWindowManagerClient::createSession had gained an int (mangled ...iiiim ->
...iiiiim). A missing symbol fails loudly at load time; a changed signature fails silently, because a caller that
still uses the old calling convention reads the wrong argument slots. So besides added / removed exports this lists:
  * drift     a removed export whose demangled qualified name (without the parameter list) reappears with a
              different mangled name -- the same function with a new signature;
  * consumer  every undefined symbol of each --consumer library that the old build defined and the new one does
              not (a load failure on the board).
Exit 0 = no drift and no consumer break, 1 = drift or consumer break, 2 = tool / usage error.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

NM = shutil.which('llvm-nm') or 'nm'
CXXFILT = shutil.which('llvm-cxxfilt') or shutil.which('c++filt') or 'c++filt'


def symbols(path, defined=True):
    flag = '--defined-only' if defined else '--undefined-only'
    out = subprocess.run([NM, '-D', flag, '--format=just-symbols', path], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f'{NM} failed on {path}: {out.stderr.strip()}')
    return {s.split('@')[0] for s in out.stdout.split() if s}


def demangle(names):
    names = sorted(names)
    if not names:
        return {}
    out = subprocess.run([CXXFILT], input='\n'.join(names), capture_output=True, text=True).stdout.splitlines()
    return dict(zip(names, out))


def base_name(demangled):
    """Qualified function name without the parameter list (and without trailing cv / ref qualifiers)."""
    depth, cut = 0, None
    for i, ch in enumerate(demangled):  # first '(' at template depth 0 opens the parameter list
        if ch == '<':
            depth += 1
        elif ch == '>':
            depth -= 1
        elif ch == '(' and depth == 0:
            cut = i
            break
    return demangled[:cut] if cut is not None else demangled


def compare(old, new, names, consumers):
    removed, added = sorted(old - new), sorted(new - old)
    by_base = {}
    for sym in added:
        if sym.startswith('_Z'):
            by_base.setdefault(base_name(names.get(sym, sym)), []).append(sym)
    drift = []
    for sym in removed:
        if sym.startswith('_Z'):
            b = base_name(names.get(sym, sym))
            for other in by_base.get(b, []):
                drift.append({'function': b, 'old': sym, 'new': other,
                              'old_signature': names.get(sym, sym), 'new_signature': names.get(other, other)})
    breaks = [{'consumer': c, 'symbol': s, 'demangled': names.get(s, s)}
              for c, undef in sorted(consumers.items()) for s in sorted(undef & (old - new))]
    return {'removed': removed, 'added': added, 'drift': drift, 'consumer_breaks': breaks}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--consumer', action='append', default=[])
    ap.add_argument('--json')
    args = ap.parse_args(argv)
    old, new = symbols(args.old), symbols(args.new)
    consumers = {c: symbols(c, defined=False) for c in args.consumer}
    names = demangle(old | new | set().union(*consumers.values()) if consumers else old | new)
    rep = compare(old, new, names, consumers)
    ident = lambda f: {'file': os.path.basename(f), 'sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest()}
    rep.update(old=ident(args.old), new=ident(args.new), consumers=[ident(c) for c in args.consumer])  # no user paths
    print(f'exports: old {len(old)}, new {len(new)}; removed {len(rep["removed"])}, added {len(rep["added"])}; '
          f'signature drift {len(rep["drift"])}; consumer breaks {len(rep["consumer_breaks"])}')
    shown = set()
    for d in rep['drift']:  # constructor / destructor variants (C1/C2, D0/D1/D2) share one signature pair
        if (d['old_signature'], d['new_signature']) not in shown:
            shown.add((d['old_signature'], d['new_signature']))
            print(f'  DRIFT {d["old_signature"]}\n     -> {d["new_signature"]}')
    for b in rep['consumer_breaks']:
        print(f'  BREAK {b["consumer"]}: {b["demangled"]}')
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(rep, fh, indent=1)
    return 1 if rep['drift'] or rep['consumer_breaks'] else 0


if __name__ == '__main__':
    sys.exit(main())
