#!/usr/bin/env python3
"""List every method and field of the given classes from a jar's dex files.

Same dex walk as dexnatives.py, but without the ACC_NATIVE filter -- used to find
the exact obtain()/setter signatures a given AOSP build actually shipped, since
android.app.servertransaction.* changed shape several times across API levels.
"""
import sys, zipfile, struct

ACC = [(0x0001,'public'),(0x0002,'private'),(0x0004,'protected'),(0x0008,'static'),
       (0x0010,'final'),(0x0100,'native'),(0x0400,'abstract')]

def uleb(b, o):
    r = 0; s = 0
    while True:
        c = b[o]; o += 1
        r |= (c & 0x7f) << s
        if c < 0x80: return r, o
        s += 7

def flagstr(a):
    return ','.join(n for m, n in ACC if a & m) or '-'

class Dex:
    def __init__(self, d):
        self.d = d
        (self.string_ids_size, self.string_ids_off) = struct.unpack_from('<II', d, 0x38)
        (self.type_ids_size, self.type_ids_off) = struct.unpack_from('<II', d, 0x40)
        (self.proto_ids_size, self.proto_ids_off) = struct.unpack_from('<II', d, 0x48)
        (self.field_ids_size, self.field_ids_off) = struct.unpack_from('<II', d, 0x50)
        (self.method_ids_size, self.method_ids_off) = struct.unpack_from('<II', d, 0x58)
        (self.class_defs_size, self.class_defs_off) = struct.unpack_from('<II', d, 0x60)
    def string(self, i):
        off = struct.unpack_from('<I', self.d, self.string_ids_off + 4*i)[0]
        n, o = uleb(self.d, off)
        end = self.d.index(b'\0', o)
        return self.d[o:end].decode('utf-8', 'replace')
    def typ(self, i):
        return self.string(struct.unpack_from('<I', self.d, self.type_ids_off + 4*i)[0])
    def proto(self, i):
        off = self.proto_ids_off + 12*i
        shorty, ret, params_off = struct.unpack_from('<III', self.d, off)
        ps = []
        if params_off:
            n = struct.unpack_from('<I', self.d, params_off)[0]
            for k in range(n):
                ps.append(self.typ(struct.unpack_from('<H', self.d, params_off+4+2*k)[0]))
        return '(' + ''.join(ps) + ')' + self.typ(ret)
    def method(self, i):
        cls, proto, name = struct.unpack_from('<HHI', self.d, self.method_ids_off + 8*i)
        return self.typ(cls), self.string(name), self.proto(proto)
    def field(self, i):
        cls, typ, name = struct.unpack_from('<HHI', self.d, self.field_ids_off + 8*i)
        return self.typ(cls), self.string(name), self.typ(typ)
    def classes(self):
        for i in range(self.class_defs_size):
            off = self.class_defs_off + 32*i
            cls_idx, flags, super_idx, ifaces, src, ann, cdata, statics = \
                struct.unpack_from('<IIIIIIII', self.d, off)
            yield self.typ(cls_idx), self.typ(super_idx) if super_idx != 0xffffffff else '?', cdata

def dump(dex, want, out):
    for name, sup, cdata in dex.classes():
        if name not in want or not cdata: continue
        out.append(('CLASS', name, 'extends ' + sup, ''))
        o = cdata
        sf, o = uleb(dex.d, o); inf, o = uleb(dex.d, o)
        dm, o = uleb(dex.d, o); vm, o = uleb(dex.d, o)
        for kind, n in (('SFIELD', sf), ('IFIELD', inf)):
            idx = 0
            for _ in range(n):
                di, o = uleb(dex.d, o); acc, o = uleb(dex.d, o)
                idx += di
                c, fn, ft = dex.field(idx)
                out.append((kind, c, fn, ft + ' [' + flagstr(acc) + ']'))
        for kind, n in (('DMETHOD', dm), ('VMETHOD', vm)):
            idx = 0
            for _ in range(n):
                di, o = uleb(dex.d, o); acc, o = uleb(dex.d, o); _, o = uleb(dex.d, o)
                idx += di
                c, mn, pr = dex.method(idx)
                out.append((kind, c, mn, pr + ' [' + flagstr(acc) + ']'))

jar = sys.argv[1]
want = set(sys.argv[2:])
z = zipfile.ZipFile(jar)
out = []
for n in z.namelist():
    if not n.endswith('.dex'): continue
    try: dex = Dex(z.read(n))
    except Exception: continue
    dump(dex, want, out)
for row in out:
    print('\t'.join(row))
print('# total %d' % len(out), file=sys.stderr)
