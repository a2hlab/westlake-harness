#!/usr/bin/env python3
"""Methods / fields an APK references on boot-classpath STUB classes that the stub does not define.

    stub_member_gap.py <app.apk> <stubs.jar> [<stubs.jar> ...] [--csv out.csv]

A stub JAR (route-A adapter-mainline-stubs.jar) declares a mainline class with only the members someone needed so
far. ART resolves an app's call against the class the BCP defines, so a referenced member the stub lacks is a
NoSuchMethodError / NoSuchFieldError at the first call -- the U10 toutiao CronetInit thread died on exactly that:
`No virtual method getSubtype()I in class Landroid/net/NetworkInfo; (declaration ... adapter-mainline-stubs.jar)`.

For every member reference in every classes*.dex of the APK whose owner class is defined by one of the stub JARs,
look the member up in that class, its stub superclasses and stub interfaces. Not found -> a row. Where the
hierarchy leaves the stub JARs (super is java.lang.Object or a framework class) only java.lang.Object's own
methods are assumed present; any other miss there is marked `super_outside_stubs` (may be inherited -- read it).
Pure dex parsing, no device; the per-member call-site class list comes from the APK's own code items.
"""
import argparse
import collections
import csv
import struct
import sys
import zipfile

OBJECT_METHODS = {'<init>', 'equals', 'hashCode', 'toString', 'getClass', 'notify', 'notifyAll', 'wait', 'clone',
                  'finalize'}


def uleb(data, pos):
    result, shift = 0, 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7f) << shift
        if b < 0x80:
            return result, pos
        shift += 7


class Dex:
    def __init__(self, data):
        self.d = data
        u = lambda off: struct.unpack_from('<I', data, off)[0]
        self.n_str, self.o_str = u(0x38), u(0x3c)
        self.n_type, self.o_type = u(0x40), u(0x44)
        self.n_proto, self.o_proto = u(0x48), u(0x4c)
        self.n_field, self.o_field = u(0x50), u(0x54)
        self.n_meth, self.o_meth = u(0x58), u(0x5c)
        self.n_cls, self.o_cls = u(0x60), u(0x64)
        self._s = {}

    def string(self, i):
        if i not in self._s:
            off = struct.unpack_from('<I', self.d, self.o_str + 4 * i)[0]
            _, p = uleb(self.d, off)
            end = self.d.index(b'\0', p)
            self._s[i] = self.d[p:end].decode('utf-8', 'replace')
        return self._s[i]

    def type(self, i):
        return self.string(struct.unpack_from('<I', self.d, self.o_type + 4 * i)[0])

    def proto(self, i):
        _, ret, params = struct.unpack_from('<III', self.d, self.o_proto + 12 * i)
        args = ''
        if params:
            n = struct.unpack_from('<I', self.d, params)[0]
            args = ''.join(self.type(struct.unpack_from('<H', self.d, params + 4 + 2 * k)[0]) for k in range(n))
        return f'({args}){self.type(ret)}'

    def method(self, i):
        cls, proto, name = struct.unpack_from('<HHI', self.d, self.o_meth + 8 * i)
        return self.type(cls), self.string(name), self.proto(proto)

    def field(self, i):
        cls, typ, name = struct.unpack_from('<HHI', self.d, self.o_field + 8 * i)
        return self.type(cls), self.string(name), self.type(typ)

    def class_defs(self):
        for k in range(self.n_cls):
            cls, acc, sup, ifaces, _, _, data_off, _ = struct.unpack_from('<IIIIIIII', self.d, self.o_cls + 32 * k)
            names = []
            if ifaces:
                n = struct.unpack_from('<I', self.d, ifaces)[0]
                names = [self.type(struct.unpack_from('<H', self.d, ifaces + 4 + 2 * j)[0]) for j in range(n)]
            yield (self.type(cls), None if sup == 0xffffffff else self.type(sup), names, data_off)

    def class_members(self, data_off):
        """-> (field_idx list, [(method_idx, code_off)])"""
        if not data_off:
            return [], []
        p = data_off
        counts = []
        for _ in range(4):
            v, p = uleb(self.d, p)
            counts.append(v)
        fields, methods = [], []
        for n in counts[:2]:
            idx = 0
            for _ in range(n):
                diff, p = uleb(self.d, p)
                _, p = uleb(self.d, p)
                idx += diff
                fields.append(idx)
        for n in counts[2:]:
            idx = 0
            for _ in range(n):
                diff, p = uleb(self.d, p)
                _, p = uleb(self.d, p)
                code, p = uleb(self.d, p)
                idx += diff
                methods.append((idx, code))
        return fields, methods


def dex_files(path):
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            if name.startswith('classes') and name.endswith('.dex'):
                yield name, z.read(name)


def load_stubs(jars):
    """class -> {'super', 'ifaces', 'methods': {(name, proto)}, 'fields': {name}, 'jar'}"""
    out = {}
    for jar in jars:
        for _, data in dex_files(jar):
            dx = Dex(data)
            for cls, sup, ifaces, data_off in dx.class_defs():
                fields, methods = dx.class_members(data_off)
                out[cls] = {'super': sup, 'ifaces': ifaces, 'jar': jar.split('/')[-1],
                            'methods': {dx.method(m)[1:] for m, _ in methods},
                            'fields': {dx.field(f)[1] for f in fields}}
    return out


def lookup(stubs, cls, kind, key, seen=None):
    """'found' | 'missing' | 'super_outside_stubs'"""
    seen = seen or set()
    if cls in seen:
        return 'missing'
    seen.add(cls)
    c = stubs.get(cls)
    if c is None:
        return 'super_outside_stubs'
    if key in c[kind]:
        return 'found'
    if kind == 'methods' and key[0] == '<init>':
        return 'missing'      # constructors are not inherited
    results = [lookup(stubs, s, kind, key, seen) for s in ([c['super']] if c['super'] else []) + c['ifaces']]
    if 'found' in results:
        return 'found'
    outside = c['super'] not in stubs and c['super'] not in (None, 'Ljava/lang/Object;')
    if 'super_outside_stubs' in results and outside:
        return 'super_outside_stubs'
    return 'missing'


INVOKE_OPS = set(range(0x6e, 0x73)) | set(range(0x74, 0x79))   # invoke-* and invoke-*/range: method idx at +2
FIELD_OPS = set(range(0x52, 0x6e))                              # iget*/iput*/sget*/sput*: field idx at +2


ERROR_CATCHERS = {'Ljava/lang/Throwable;', 'Ljava/lang/Error;', 'Ljava/lang/LinkageError;',
                  'Ljava/lang/IncompatibleClassChangeError;', 'Ljava/lang/NoSuchMethodError;',
                  'Ljava/lang/NoSuchFieldError;'}


def sleb(data, pos):
    result, shift = 0, 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7f) << shift
        shift += 7
        if b < 0x80:
            if b & 0x40:
                result -= 1 << shift
            return result, pos


def catch_all_kind(dx, base, insns_size, addr, limit=80):
    """D8 compiles `catch (Throwable t)` to a catch-all, the same encoding as finally / synchronized. Tell them
    apart by the handler: `move-exception vA` then `throw vA` (rethrow) = finally-only; reaching a return / goto
    first = the handler swallows (counts as catches-error). Undecided within `limit` units -> finally-only."""
    unit = struct.unpack_from('<H', dx.d, base + 2 * addr)[0]
    if unit & 0xff != 0x0d:          # no move-exception: the handler ignores the exception object
        return 'catches-error'
    reg, i = unit >> 8, addr + 1
    while i < min(insns_size, addr + limit):
        unit = struct.unpack_from('<H', dx.d, base + 2 * i)[0]
        op = unit & 0xff
        if op == 0x27:
            return 'finally-only' if unit >> 8 == reg else 'catches-error'
        if 0x0e <= op <= 0x11 or op in (0x28, 0x29, 0x2a):
            return 'catches-error'
        i += WIDTH.get(op, 1)
    return 'finally-only'


def try_guards(dx, code, insns_size):
    """[(start, end, guard)] for one code item; guard 'catches-error' when a handler type would catch a
    NoSuchMethodError / NoSuchFieldError, else 'finally-only' (a catch-all, i.e. finally / synchronized: it
    rethrows) or 'exception-only' (typed handlers that cannot catch an Error)."""
    tries_size = struct.unpack_from('<H', dx.d, code + 6)[0]
    if not tries_size:
        return []
    tries_off = code + 16 + insns_size * 2
    if insns_size % 2:
        tries_off += 2
    list_off = tries_off + 8 * tries_size
    out = []
    for k in range(tries_size):
        start, count, hoff = struct.unpack_from('<IHH', dx.d, tries_off + 8 * k)
        size, p = sleb(dx.d, list_off + hoff)
        types = set()
        for _ in range(abs(size)):
            t, p = uleb(dx.d, p)
            _, p = uleb(dx.d, p)
            types.add(dx.type(t))
        if types & ERROR_CATCHERS:
            guard = 'catches-error'
        elif size <= 0:
            all_addr, _ = uleb(dx.d, p)
            guard = catch_all_kind(dx, code + 16, insns_size, all_addr)
        else:
            guard = 'exception-only'
        out.append((start, start + count, guard))
    return out


def callers(dx, wanted_methods, wanted_fields):
    """(kind, member index) -> {(calling class, calling method, guard)} from the APK's own code items. guard is
    the best local try/catch cover of the call site: 'catches-error' > 'finally-only' / 'exception-only' > 'none'.
    A site not caught locally may still be caught by a caller further up -- 'none' is local only."""
    hits = collections.defaultdict(set)
    for cls, _, _, data_off in dx.class_defs():
        _, methods = dx.class_members(data_off)
        for midx, code in methods:
            if not code:
                continue
            insns_size = struct.unpack_from('<I', dx.d, code + 12)[0]
            guards = None
            base, i = code + 16, 0
            while i < insns_size:
                unit = struct.unpack_from('<H', dx.d, base + 2 * i)[0]
                op = unit & 0xff
                if op == 0x00 and unit in (0x0100, 0x0200, 0x0300):   # packed / sparse switch, fill-array payload
                    if unit == 0x0100:
                        size = struct.unpack_from('<H', dx.d, base + 2 * i + 2)[0]
                        i += size * 2 + 4
                    elif unit == 0x0200:
                        size = struct.unpack_from('<H', dx.d, base + 2 * i + 2)[0]
                        i += size * 4 + 2
                    else:
                        width = struct.unpack_from('<H', dx.d, base + 2 * i + 2)[0]
                        count = struct.unpack_from('<I', dx.d, base + 2 * i + 4)[0]
                        i += (count * width + 1) // 2 + 4
                    continue
                key = None
                if op in INVOKE_OPS or op in FIELD_OPS:
                    idx = struct.unpack_from('<H', dx.d, base + 2 * i + 2)[0]
                    if op in INVOKE_OPS and idx in wanted_methods:
                        key = ('m', idx)
                    elif op in FIELD_OPS and idx in wanted_fields:
                        key = ('f', idx)
                if key:
                    if guards is None:
                        guards = try_guards(dx, code, insns_size)
                    cover = [g for s0, e0, g in guards if s0 <= i < e0]
                    guard = ('catches-error' if 'catches-error' in cover else
                             'finally-only' if 'finally-only' in cover else
                             'exception-only' if cover else 'none')
                    hits[key].add((cls, dx.method(midx)[1], guard))
                i += WIDTH.get(op, 1)
    return hits


# dalvik instruction widths in 16-bit code units (opcode -> units); default 1
WIDTH = {}
for ops, w in (((0x02, 0x05, 0x08, 0x13, 0x15, 0x16, 0x19, 0x1a, 0x1c, 0x1f, 0x20, 0x22, 0x23, 0x29), 2),
               ((0x03, 0x06, 0x09, 0x14, 0x17, 0x1b, 0x24, 0x25, 0x26, 0x2a, 0x2b, 0x2c), 3),
               ((0x18,), 5), ((0x2d, 0x2e, 0x2f, 0x30, 0x31), 2),
               (tuple(range(0x32, 0x3e)), 2), (tuple(range(0x44, 0x6e)), 2), (tuple(range(0x6e, 0x73)), 3),
               (tuple(range(0x74, 0x79)), 3), (tuple(range(0x90, 0xb0)), 2), (tuple(range(0xd0, 0xe3)), 2),
               ((0xfa, 0xfb), 4), ((0xfc, 0xfd), 3), ((0xfe, 0xff), 2)):
    for o in ops:
        WIDTH[o] = w


def scan(apk, stubs):
    rows = {}
    for dex_name, data in dex_files(apk):
        dx = Dex(data)
        want_m, want_f = {}, {}
        for i in range(dx.n_meth):
            cls, name, proto = dx.method(i)
            if cls in stubs:
                verdict = lookup(stubs, cls, 'methods', (name, proto))
                if verdict != 'found' and not (name in OBJECT_METHODS and name != '<init>'):  # resolve on Object
                    want_m[i] = (cls, name + proto, 'method', verdict)
        for i in range(dx.n_field):
            cls, name, typ = dx.field(i)
            if cls in stubs:
                verdict = lookup(stubs, cls, 'fields', name)
                if verdict != 'found':
                    want_f[i] = (cls, f'{name}:{typ}', 'field', verdict)
        if not want_m and not want_f:
            continue
        hits = callers(dx, want_m, want_f)
        for table, kind in ((want_m, 'm'), (want_f, 'f')):
            for idx, (cls, member, what, verdict) in table.items():
                row = rows.setdefault((cls, member), {'class': cls, 'member': member, 'kind': what, 'verdict': verdict,
                                                     'stub_jar': stubs[cls]['jar'], 'dex': set(), 'callers': set(),
                                                     'sites': set()})
                row['dex'].add(dex_name)
                for caller_cls, caller_m, guard in hits.get((kind, idx), set()):
                    row['callers'].add(caller_cls)
                    row['sites'].add((caller_cls, caller_m, guard))
    return sorted(rows.values(), key=lambda r: (r['verdict'] != 'missing', -len(r['callers']), r['class'], r['member']))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('apk')
    ap.add_argument('stubs', nargs='+')
    ap.add_argument('--csv')
    args = ap.parse_args()
    stubs = load_stubs(args.stubs)
    rows = scan(args.apk, stubs)
    for r in rows:
        unguarded = sorted({c for c, _, g in r['sites'] if g != 'catches-error'})
        print(f"{r['verdict']:20} {r['kind']:6} {r['class']}->{r['member']}  callers={len(r['callers'])} "
              f"not-caught-locally={len(unguarded)}  e.g. {', '.join(unguarded[:3])}")
    print(f'== {len(rows)} member(s) referenced on {len(stubs)} stub classes but not defined '
          f"({sum(r['verdict'] == 'missing' for r in rows)} missing, "
          f"{sum(r['verdict'] != 'missing' for r in rows)} super_outside_stubs)")
    if args.csv:
        with open(args.csv, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['verdict', 'kind', 'class', 'member', 'stub_jar', 'caller_count', 'sites_not_caught_locally',
                        'sites', 'dex'])
            for r in rows:
                sites = sorted(r['sites'])
                w.writerow([r['verdict'], r['kind'], r['class'], r['member'], r['stub_jar'], len(r['callers']),
                            sum(g != 'catches-error' for _, _, g in sites),
                            ' '.join(f'{c}->{m}[{g}]' for c, m, g in sites), ' '.join(sorted(r['dex']))])
    return 0


if __name__ == '__main__':
    sys.exit(main())
