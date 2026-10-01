#!/usr/bin/env python3
"""Compare the dynamic ABI of a rebuilt library against the deployed one: exports AND call signatures.

    abi_diff.py --old <deployed.so> --new <rebuilt.so> [--consumer <lib.so> ...] [--json out.json]
    abi_diff.py --old <deployed.so> --new <rebuilt.so> --calls [--calls-grep RE]   # per-function call-set diff
    abi_diff.py --selftest --old <deployed.so> --new <rebuilt.so>                   # fixture assertions

Why (user rule 2026-10-01): a rebuild was accepted on an export-table diff ("14 missing exports, no consumers") and
on the board every app died -- OHWindowManagerClient::createSession had gained an int (mangled ...iiiim ->
...iiiiim). A missing symbol fails loudly at load time; a changed signature fails silently, because a caller that
still uses the old calling convention reads the wrong argument slots. So besides added / removed exports this lists:
  * drift     a removed export whose demangled qualified name (without the parameter list) reappears with a
              different mangled name -- the same function with a new signature;
  * consumer  every undefined symbol of each --consumer library that the old build defined and the new one does
              not (a load failure on the board).
And, with --calls (retro 2026-10-01, #96): a BODY change invisible to signature/layout diffing -- the deployed 846
SessionStageAdapter ctor attaches with a plain GetEnv, while the b68 rebuild routes through the WLTG-ticket-gated
westlake::jni::ScopedJniAttachment and yields no JNIEnv on the JNI createSession thread. The ctor's *exported
signature* and the class *layout* are identical; only its call graph differs. --calls diffs, per function present in
both builds, the set of named bl/b call targets, so "same signature, different callees" is caught statically.
Exit 0 = no drift and no consumer break, 1 = drift or consumer break, 2 = tool / usage error. (--calls is a report;
it does not by itself change the exit code -- gate on its output for the specific function you care about.)
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

NM = shutil.which('llvm-nm') or 'nm'
CXXFILT = shutil.which('llvm-cxxfilt') or shutil.which('c++filt') or 'c++filt'
# objdump is only needed for --calls. Resolve portably: env override, then PATH, then plain name.
# Never hard-code a per-machine path (land.py user-path gate); callers set LLVM_OBJDUMP if llvm-objdump
# is not on PATH (e.g. the DevEco SDK copy on a dev Mac).
OBJDUMP = os.environ.get('LLVM_OBJDUMP') or shutil.which('llvm-objdump') or shutil.which('objdump') or 'objdump'


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


_HDR = re.compile(r'^[0-9a-fA-F]+ <(.+)>:$')
_CALL = re.compile(r'^\s+[0-9a-fA-F]+:\s+(?:bl|b)\s+0x[0-9a-fA-F]+ <([^>]+)>')


def call_sets(path, objdump=OBJDUMP):
    """{function mangled-name: set of named bl/b callees}. Callees are stripped of @plt and +offset and
    self-references are dropped, so the set is the external/named call graph of each defined function.
    Pure except for the objdump subprocess; parsing is deterministic."""
    out = subprocess.run([objdump, '-d', '--no-show-raw-insn', path], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f'{objdump} failed on {path}: {out.stderr.strip() or "(no stderr)"}')
    calls, cur = {}, None
    for line in out.stdout.splitlines():
        h = _HDR.match(line)
        if h:
            cur = h.group(1)
            calls.setdefault(cur, set())
            continue
        if cur is None:
            continue
        c = _CALL.match(line)
        if c:
            tgt = c.group(1).split('@')[0].split('+')[0]
            if tgt and tgt != cur:
                calls[cur].add(tgt)
    return calls


def compare_calls(old_calls, new_calls, names):
    """For every function defined in BOTH builds, report callee-set differences (added = in new not old)."""
    diffs = []
    for fn in sorted(set(old_calls) & set(new_calls)):
        added = sorted(new_calls[fn] - old_calls[fn])
        removed = sorted(old_calls[fn] - new_calls[fn])
        if added or removed:
            diffs.append({'function': fn, 'demangled': names.get(fn, fn),
                          'added_callees': added, 'removed_callees': removed})
    return diffs


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
    ap.add_argument('--calls', action='store_true',
                    help='also diff, per function defined in both builds, the set of named bl/b call targets')
    ap.add_argument('--calls-grep', default=None,
                    help='with --calls, only print functions whose demangled name matches this regex')
    ap.add_argument('--objdump', default=OBJDUMP, help='llvm-objdump path for --calls (default: env/PATH)')
    ap.add_argument('--selftest', action='store_true',
                    help='assert --calls on (old=deployed, new=rebuilt) flags the SessionStageAdapter ctor WLTG gate')
    args = ap.parse_args(argv)
    old, new = symbols(args.old), symbols(args.new)
    consumers = {c: symbols(c, defined=False) for c in args.consumer}
    names = demangle(old | new | set().union(*consumers.values()) if consumers else old | new)
    rep = compare(old, new, names, consumers)
    ident = lambda f: {'file': os.path.basename(f), 'sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest()}
    rep.update(old=ident(args.old), new=ident(args.new), consumers=[ident(c) for c in args.consumer])  # no user paths

    call_diffs = None
    if args.calls or args.selftest:
        oc, nc = call_sets(args.old, args.objdump), call_sets(args.new, args.objdump)
        all_names = demangle(set(oc) | set(nc))
        call_diffs = compare_calls(oc, nc, all_names)
        rep['call_diffs'] = call_diffs

    if args.selftest:
        # Fixture assertion: old=deployed 846, new=a1f57197 (b68 rebuild). The b68 SessionStageAdapter ctor must
        # show the WLTG-gated attach (ScopedJniAttachment / WLTG_*) as ADDED callees that 846's ctor lacks.
        ctor = [d for d in call_diffs if 'SessionStageAdapter::SessionStageAdapter' in d['demangled']]
        hit = any(('ScopedJniAttachment' in c or c.startswith('WLTG_') or '3jni19ScopedJniAttachment' in c)
                  for d in ctor for c in d['added_callees'])
        print(f'SELFTEST SessionStageAdapter ctor WLTG-gate added-callee present: {hit}')
        for d in ctor:
            print(f'  {d["demangled"]}\n    added: {d["added_callees"]}')
        return 0 if hit else 1

    print(f'exports: old {len(old)}, new {len(new)}; removed {len(rep["removed"])}, added {len(rep["added"])}; '
          f'signature drift {len(rep["drift"])}; consumer breaks {len(rep["consumer_breaks"])}')
    shown = set()
    for d in rep['drift']:  # constructor / destructor variants (C1/C2, D0/D1/D2) share one signature pair
        if (d['old_signature'], d['new_signature']) not in shown:
            shown.add((d['old_signature'], d['new_signature']))
            print(f'  DRIFT {d["old_signature"]}\n     -> {d["new_signature"]}')
    for b in rep['consumer_breaks']:
        print(f'  BREAK {b["consumer"]}: {b["demangled"]}')
    if call_diffs is not None:
        rx = re.compile(args.calls_grep) if args.calls_grep else None
        shown_c = [d for d in call_diffs if not rx or rx.search(d['demangled'])]
        print(f'call-set diffs: {len(call_diffs)} function(s) differ'
              + (f', {len(shown_c)} match /{args.calls_grep}/' if rx else ''))
        for d in shown_c:
            if d['added_callees']:
                print(f'  CALLS+ {d["demangled"]}: {d["added_callees"]}')
            if d['removed_callees']:
                print(f'  CALLS- {d["demangled"]}: {d["removed_callees"]}')
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(rep, fh, indent=1)
    return 1 if rep['drift'] or rep['consumer_breaks'] else 0


if __name__ == '__main__':
    sys.exit(main())
