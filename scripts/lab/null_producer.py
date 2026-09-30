#!/usr/bin/env python3
"""Trace the instruction that produced the null in an app's first-fatal NPE.

Given a baksmali disassembly of the crashing class, the crashing method, and the
NPE target (the `invoke ... on a null object reference` from the hilog), this walks
the receiver register backward to the instruction that last wrote it, and classifies
the null's origin:

  framework   a move-result after an invoke of an android.* / adapter.* method
              -> a framework/adapter API returned null (a framework wall; fixable by
                 making that API return a non-null type-zero value)
  app         a move-result after an invoke of an app-package method, or an
              iget/sget of an app field, or an explicit `const 0` (app passed null)
  undeterminable  the producer could not be resolved (e.g. a method parameter, or a
                 register written on a branch this linear scan cannot disambiguate)

Input is baksmali smali (portable; no JVM). Disassemble with:
  java -cp <baksmali+dexlib2+util+guava+jcommander>.jar org.jf.baksmali.Main \
       disassemble app.apk -o out/   # then out/<pkg>/<Class>.smali

NPE target: pass the method name from the hilog message, e.g.
  "Attempt to invoke virtual method 'int android.content.Intent.getIntExtra(...)'"
  -> --npe android.content.Intent.getIntExtra
For a getClass()-based Kotlin/R8 null check the hilog says java.lang.Object.getClass;
pass --npe java.lang.Object.getClass and (usually) --line from the frame.
"""
import argparse
import json
import re
import sys

# Framework / our-adapter package prefixes: a null from one of these = a framework wall.
FRAMEWORK_PREFIXES = ('Landroid/', 'Ljava/', 'Ljavax/', 'Lorg/apache/', 'Lorg/json/',
                      'Lorg/w3c/', 'Lorg/xml/', 'Ldalvik/', 'Llibcore/')
ADAPTER_PREFIXES = ('Ladapter/', 'Lcom/android/internal/', 'Lcom/android/org/')

# Framework Context/Activity/View/etc. methods that apps call on their OWN subclass
# (so the invoke's class is the app package, but the behaviour is framework / our adapter).
# Classify a null from one of these as framework regardless of the static class.
FRAMEWORK_METHODS = frozenset((
    'registerReceiver', 'getApplicationContext', 'getSystemService', 'getContentResolver',
    'getPackageManager', 'getBaseContext', 'getIntent', 'getApplicationInfo', 'peekService',
    'getExternalFilesDir', 'getExternalCacheDir', 'getFilesDir', 'getCacheDir', 'getDir',
    'getDatabasePath', 'getSharedPreferences', 'getAssets', 'getResources', 'getClassLoader',
    'getMainLooper', 'getWindow', 'getWindowManager', 'getLayoutInflater',
))

INVOKE_RE = re.compile(r'^\s*(invoke-\S+)\s+\{([^}]*)\}\s*,\s*(L[^;]+;)->(\S+?)\((.*?)\)(\S+)\s*$')
MOVE_RESULT_RE = re.compile(r'^\s*move-result(?:-object|-wide)?\s+([vp]\d+)\s*$')
IGET_RE = re.compile(r'^\s*i(get|put)-\S+\s+([vp]\d+),\s*([vp]\d+),\s*(L[^;]+;->\S+)\s*$')
SGET_RE = re.compile(r'^\s*s(get|put)-\S+\s+([vp]\d+),\s*(L[^;]+;->\S+)\s*$')
CONST_RE = re.compile(r'^\s*const(?:/4|/16|-wide/\d+|/high16|)\s+([vp]\d+),\s*(\S+)\s*$')
MOVE_RE = re.compile(r'^\s*move(?:-object|-wide|)(?:/from16|/16|)\s+([vp]\d+),\s*([vp]\d+)\s*$')
LINE_RE = re.compile(r'^\s*\.line\s+(\d+)\s*$')


def parse_method(smali_text, method_name):
    """Return the list of raw instruction lines for the first method whose name matches,
    plus the method's register declaration line, or (None, None)."""
    lines = smali_text.splitlines()
    out, decl, in_m = [], None, False
    for ln in lines:
        s = ln.strip()
        if not in_m and s.startswith('.method') and ('>' + method_name + '(' in ('>' + ln)
                                                      or (' ' + method_name + '(') in (' ' + s)
                                                      or s.split('(')[0].endswith(' ' + method_name)):
            in_m, decl = True, s
            out = []
            continue
        if in_m:
            if s.startswith('.end method'):
                break
            out.append(ln)
    return (out, decl) if in_m else (None, None)


def receiver_reg(invoke_text):
    """First register of an invoke (the receiver for virtual/interface/direct/super)."""
    m = INVOKE_RE.match(invoke_text)
    if not m:
        return None, None
    kind, regs, cls, meth, args, ret = m.groups()
    # "{v6, v7, v10}" or range "{v0 .. v3}"; the receiver is the first listed register.
    regs = [r.strip() for r in regs.replace('..', ',').split(',') if r.strip()]
    first = regs[0] if regs else None
    return first, (kind, cls, meth, args, ret)


def find_npe_invoke(insns, npe_cls, npe_meth, line=None):
    """Index of the invoke of npe_cls->npe_meth; if line is given, the first such invoke
    at or after that .line; else the first one."""
    want_cls = 'L' + npe_cls.replace('.', '/') + ';'
    after = line is None
    cur_line = None
    hits = []
    for i, ln in enumerate(insns):
        lm = LINE_RE.match(ln)
        if lm:
            cur_line = int(lm.group(1))
            if line is not None and cur_line >= line:
                after = True
            continue
        m = INVOKE_RE.match(ln)
        if m and m.group(3) == want_cls and m.group(4) == npe_meth:
            hits.append((i, after, cur_line))
    if not hits:
        return None
    # prefer the first hit at/after the crash line, else the first hit overall
    for i, ok, _ in hits:
        if ok:
            return i
    return hits[0][0]


def trace_producer(insns, invoke_idx, reg, max_back=400):
    """Walk backward from invoke_idx for the last write of reg. Follows one move-object
    alias hop. Returns a dict describing the producer."""
    hops = 0
    idx = invoke_idx
    target = reg
    while hops < 4:
        for j in range(idx - 1, max(-1, idx - max_back), -1):
            ln = insns[j]
            mr = MOVE_RESULT_RE.match(ln)
            if mr and mr.group(1) == target:
                # producer is the nearest preceding invoke
                for k in range(j - 1, max(-1, j - 6), -1):
                    inv = INVOKE_RE.match(insns[k])
                    if inv:
                        return {'kind': 'invoke-return', 'cls': inv.group(3),
                                'method': inv.group(4) + '(' + inv.group(5) + ')' + inv.group(6),
                                'insn': insns[k].strip(), 'via': insns[j].strip()}
                return {'kind': 'move-result-orphan', 'insn': insns[j].strip()}
            ig = IGET_RE.match(ln)
            if ig and ig.group(1) == 'get' and ig.group(2) == target:
                return {'kind': 'field', 'field': ig.group(4), 'insn': ln.strip()}
            sg = SGET_RE.match(ln)
            if sg and sg.group(1) == 'get' and sg.group(2) == target:
                return {'kind': 'static-field', 'field': sg.group(3), 'insn': ln.strip()}
            cm = CONST_RE.match(ln)
            if cm and cm.group(1) == target:
                return {'kind': 'const', 'value': cm.group(2), 'insn': ln.strip()}
            mv = MOVE_RE.match(ln)
            if mv and mv.group(1) == target:
                target = mv.group(2)  # alias: keep tracing the source register
                idx = j
                hops += 1
                break
        else:
            break
    if target.startswith('p'):
        return {'kind': 'param', 'reg': target}
    return {'kind': 'undeterminable', 'reg': target}


def classify(producer):
    if producer['kind'] == 'invoke-return':
        cls = producer['cls']
        name = producer['method'].split('(')[0]
        if cls.startswith(ADAPTER_PREFIXES) or cls.startswith(FRAMEWORK_PREFIXES):
            return 'framework', f"{cls}->{producer['method']} returned null"
        if name in FRAMEWORK_METHODS:
            return 'framework', (f"{cls}->{producer['method']} returned null "
                                 f"(inherited framework Context/Activity method)")
        return 'app', f"app method {cls}->{producer['method']} returned null"
    if producer['kind'] in ('field', 'static-field'):
        fld = producer['field']
        if fld.startswith(ADAPTER_PREFIXES) or fld.startswith(FRAMEWORK_PREFIXES):
            return 'framework', f"framework field {fld} is null"
        return 'app', f"app field {fld} is null"
    if producer['kind'] == 'const':
        return 'app', f"explicit null literal ({producer['value']}) passed by the app"
    if producer['kind'] == 'param':
        return 'undeterminable', f"null arrived as method parameter {producer['reg']} (trace the caller)"
    return 'undeterminable', 'producer register write not found by linear back-scan'


def analyze(smali_text, method, npe_cls, npe_meth, line=None):
    insns, decl = parse_method(smali_text, method)
    if insns is None:
        return {'error': f'method {method} not found'}
    idx = find_npe_invoke(insns, npe_cls, npe_meth, line)
    if idx is None:
        return {'error': f'no invoke of {npe_cls}.{npe_meth} in {method}'}
    reg, sig = receiver_reg(insns[idx])
    producer = trace_producer(insns, idx, reg)
    category, detail = classify(producer)
    return {
        'method': method, 'npe': f'{npe_cls}.{npe_meth}', 'crash_line': line,
        'npe_insn': insns[idx].strip(), 'receiver': reg,
        'producer': producer, 'category': category, 'detail': detail,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--smali', required=True, help='baksmali .smali file of the crashing class')
    ap.add_argument('--method', required=True, help='crashing method name (e.g. onCreate, resolveRestrictions)')
    ap.add_argument('--npe', required=True, help='NPE target method, dotted (e.g. android.content.Intent.getIntExtra)')
    ap.add_argument('--line', type=int, help='crash line from the frame (.line in smali)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    npe_cls, _, npe_meth = a.npe.rpartition('.')
    if not npe_cls:
        print('--npe must be a dotted class.method, e.g. android.content.Intent.getIntExtra', file=sys.stderr)
        return 2
    res = analyze(open(a.smali, errors='replace').read(), a.method, npe_cls, npe_meth, a.line)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        if 'error' in res:
            print('error:', res['error']); return 1
        print(f"method       {res['method']}  (crash line {res['crash_line']})")
        print(f"NPE          {res['npe']} on {res['receiver']}")
        print(f"npe insn     {res['npe_insn']}")
        print(f"producer     {res['producer'].get('insn', res['producer'])}")
        print(f"category     {res['category'].upper()}")
        print(f"detail       {res['detail']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
