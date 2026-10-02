#!/usr/bin/env python3
"""Instruction-level equivalence of two builds of the same library, function by function, with every address operand
resolved to what it points at.

    equiv.py <deployed .so> <rebuilt .so> [--show]

Both binaries are disassembled once (llvm-objdump -d). For every instruction the address column is dropped and
address operands are replaced by their meaning, so link layout cancels out but behaviour does not:
  * adrp page + the following add/ldr/str low-12 offset on that register -> the C string it points at
    (STR"...", from .rodata/.data.rel.ro) or the data/text symbol (SYM name+off), else ADDR;
  * adr / literal loads -> the same resolution;
  * bl/b targets -> callee symbol (PLT stubs -> import name); branches inside the function -> offset from the
    function start (L+0x..), which is equal only when the code before it is equal.
Register choice, constants (field offsets, #0x3e9) and instruction order are kept. Page tracking is linear. A function
that still differs only in [reg, #off] operands whose register tracking was lost (a page register restored in one
epilogue and still live on a cold path laid out after it) gets a second, local pass: each such operand is resolved
through every `adrp reg` of that function; when the same adrp (same instruction index in both builds) gives the same
named symbol in both, the operand counts as equal. Such functions are reported as EQUAL-AFTER-RESIDUAL with the
resolved operand and the adrp used, so the claim can be checked by hand. A function is EQUAL when its
resolved instruction list is identical.
"""
import re
import subprocess
import sys
from bisect import bisect_right


def tool(name):
    return subprocess.run(['xcrun', '-f', name], capture_output=True, text=True).stdout.strip() or name


class Image:
    def __init__(self, so):
        self.so = so
        self.data = open(so, 'rb').read()
        out = subprocess.run([tool('llvm-readelf'), '-S', '-W', so], capture_output=True, text=True).stdout
        self.secs = []
        for line in out.splitlines():
            m = re.search(r'\]\s+(\S+)\s+\S+\s+([0-9a-f]{8,})\s+([0-9a-f]+)\s+([0-9a-f]+)', line)
            if m:
                self.secs.append((m.group(1), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)))
        nm = subprocess.run([tool('llvm-nm'), '-n', '-S', '--defined-only', '-C', so], capture_output=True, text=True).stdout
        self.syms = []
        for line in nm.splitlines():
            f = line.split(' ', 3)
            if len(f) == 4:
                self.syms.append((int(f[0], 16), int(f[1], 16), f[3]))
            elif len(f) == 3:
                self.syms.append((int(f[0], 16), 0, f[2]))
        self.syms.sort()
        self.addrs = [s[0] for s in self.syms]
        # relocated pointer slots (GOT entries, vtables): slot -> what the dynamic linker will store there
        self.slots = {}
        rel = subprocess.run([tool('llvm-readelf'), '-r', '-W', '-C', so], capture_output=True, text=True).stdout
        for line in rel.splitlines():
            f = line.split()
            if len(f) >= 3 and re.fullmatch(r'[0-9a-f]{8,}', f[0]):
                if f[2] == 'R_AARCH64_RELATIVE' and len(f) >= 4:
                    self.slots[int(f[0], 16)] = ('REL', int(f[3], 16))
                elif f[2] in ('R_AARCH64_GLOB_DAT', 'R_AARCH64_ABS64') and len(f) >= 5:
                    name = ' '.join(f[4:]).rsplit(' + ', 1)[0]
                    self.slots[int(f[0], 16)] = ('SYM', name)
        # PLT: objdump names stubs <name@plt>; collected while disassembling

    def cstr(self, addr):
        for name, va, off, size in self.secs:
            if name.startswith('.rodata') and va <= addr < va + size:
                o = off + addr - va
                end = self.data.find(b'\0', o, o + 300)
                if end <= o:
                    return None
                try:
                    t = self.data[o:end].decode()
                except UnicodeDecodeError:
                    return None
                if len(t) >= 2 and all(31 < ord(c) < 127 or c in '\t\n' for c in t):
                    return t
        return None

    def resolve(self, addr, follow=True):
        if follow and addr in self.slots:
            kind, v = self.slots[addr]
            return f'SLOT->{self.resolve(v, False) if kind == "REL" else "SYM " + v}'
        s = self.cstr(addr)
        if s is not None:
            return f'STR"{s[:80]}"'
        i = bisect_right(self.addrs, addr) - 1
        if i >= 0:
            a, size, name = self.syms[i]
            if size and addr < a + size:
                return f'SYM {name}+{addr - a:#x}'
            if addr == a:
                return f'SYM {name}'
        for name, va, off, size in self.secs:
            if va <= addr < va + size:
                return f'SEC {name}'
        return 'ADDR'


def functions(img):
    out = subprocess.run([tool('llvm-objdump'), '-d', '--no-show-raw-insn', img.so], capture_output=True,
                         text=True).stdout
    funcs, name, start, page, cur = {}, None, 0, {}, None
    cxxfilt, raw, key = [], {}, None
    for line in out.splitlines():
        m = re.match(r'^([0-9a-f]+) <(.+)>:$', line)
        if m:
            start, name = int(m.group(1), 16), m.group(2)
            if name.endswith('@plt') or name.startswith('$'):
                cur = None
                continue
            key = name
            k = 2
            while key in funcs:
                key = f'{name}#{k}'
                k += 1
            cur = funcs[key] = []
            raw[key] = []
            cxxfilt.append(key)
            page = {}
            continue
        m = re.match(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$', line)
        if not m or cur is None:
            continue
        pc, op, ops = int(m.group(1), 16), m.group(2), re.sub(r'\s*//.*$', '', m.group(3)).strip()
        raw.setdefault(key, []).append((op, ops))
        if op == 'adrp':
            mm = re.match(r'(x\d+),\s*0x([0-9a-f]+)', ops)
            if mm:
                page[mm.group(1)] = int(mm.group(2), 16)
                cur.append(f'adrp {mm.group(1)}, PAGE')
                continue
        if op == 'add':
            mm = re.match(r'(x\d+),\s*(x\d+),\s*#0x([0-9a-f]+)$', ops)
            if mm and mm.group(2) in page:
                cur.append(f'add {mm.group(1)}, {mm.group(2)}, ={img.resolve(page[mm.group(2)] + int(mm.group(3), 16))}')
                page.pop(mm.group(1), None)  # destination now holds a full address, not a page
                continue
        if op.startswith(('ldr', 'str', 'ldp', 'stp')):
            mm = re.search(r'\[(x\d+)(?:,\s*#0x([0-9a-f]+))?\]', ops)
            base = page.get(mm.group(1)) if mm else None
            if base is not None:
                cur.append(f'{op} {ops[:ops.index("[")]}[={img.resolve(base + int(mm.group(2) or "0", 16))}]')
                if op.startswith('ld'):
                    for r in re.findall(r'\b([xw]\d+)\b', ops[:ops.index('[')]):
                        page.pop(r.replace('w', 'x'), None)
                continue
        mm = re.match(r'(x\d+|w\d+)', ops)
        if mm and not op.startswith(('st', 'cmp', 'cmn', 'tst', 'cb', 'tb', 'prfm')) and mm.group(1).replace('w', 'x') in page:
            page.pop(mm.group(1).replace('w', 'x'), None)  # register overwritten
        if op in ('adr',) or (op.startswith('ldr') and re.search(r',\s*0x[0-9a-f]+', ops)):
            mm = re.search(r'0x([0-9a-f]+)', ops)
            cur.append(f'{op} {ops.split(",")[0]}, ={img.resolve(int(mm.group(1), 16))}')
            continue
        if op in ('bl', 'b') or op.startswith('b.') or op in ('cbz', 'cbnz', 'tbz', 'tbnz'):
            mm = re.search(r'0x([0-9a-f]+)\s*<([^>]+)>', ops)
            if mm:
                tgt, sym = int(mm.group(1), 16), mm.group(2)
                head = ops[:ops.index('0x')]
                if '+' in sym or sym == name:
                    cur.append(f'{op} {head}L+{tgt - start:#x}')
                else:
                    cur.append(f'{op} {head}{sym.replace("@plt", "")}')
                continue
        cur.append(f'{op} {ops}')
    img.raw = raw
    return funcs


def residual(img, name, i):
    """Candidate meanings of insn i of function name: its [reg, #off] resolved through every `adrp reg` in the
    function, as {adrp index: resolution}."""
    op, ops = img.raw[name][i]
    mm = re.search(r'\[(x\d+),\s*#0x([0-9a-f]+)\]', ops)
    if not mm:
        return {}
    out = {}
    for j, (pop, pops) in enumerate(img.raw[name]):
        m2 = re.match(r'(x\d+),\s*0x([0-9a-f]+)', pops)
        if pop == 'adrp' and m2 and m2.group(1) == mm.group(1):
            out[j] = f'{op} {ops[:ops.index("[")]}[={img.resolve(int(m2.group(2), 16) + int(mm.group(2), 16))}]'
    return out


def residual_match(a, b, name, i):
    """The same adrp (same index in both functions) gives the same named symbol in both -> that resolution."""
    ra, rb = residual(a, name, i), residual(b, name, i)
    for j in sorted(ra):
        if j in rb and ra[j] == rb[j] and '=SYM ' in ra[j]:
            return f'{ra[j]} (via adrp #{j})'
    return None


def demangle(names):
    out = subprocess.run([tool('llvm-cxxfilt')], input='\n'.join(names), capture_output=True, text=True).stdout
    return dict(zip(names, out.splitlines()))


def main():
    a, b = Image(sys.argv[1]), Image(sys.argv[2])
    show = '--show' in sys.argv
    fa, fb = functions(a), functions(b)
    common = sorted(set(fa) & set(fb))
    diff, residual_ok = [], []
    for n in common:
        if fa[n] == fb[n]:
            continue
        idx = [i for i, (x, y) in enumerate(zip(fa[n], fb[n])) if x != y]
        if len(fa[n]) == len(fb[n]) and idx:
            rs = [residual_match(a, b, n, i) for i in idx]
            if all(rs):
                residual_ok.append((n, list(zip(idx, rs))))
                continue
        diff.append(n)
    dm = demangle(sorted(set(fa) | set(fb)))
    print(f'functions: deployed {len(fa)}, rebuilt {len(fb)}, common {len(common)}, '
          f'instruction-equal {len(common) - len(diff) - len(residual_ok)} (+{len(residual_ok)} after residual '
          f'resolution), differ {len(diff)}, '
          f'only deployed {len(set(fa) - set(fb))}, only rebuilt {len(set(fb) - set(fa))}')
    for n, items in residual_ok:
        print(f'  EQUAL-AFTER-RESIDUAL {dm.get(n, n)[:120]}: ' + '; '.join(f'insn {i}: {r[:90]}' for i, r in items))
    for n in diff:
        print(f'  DIFF {dm.get(n, n)[:150]}  ({len(fa[n])} -> {len(fb[n])} insns)')
        if show:
            for i, (x, y) in enumerate(zip(fa[n], fb[n])):
                if x != y:
                    print(f'      first divergence at insn {i}: {x[:110]}  |  {y[:110]}')
                    break
    for n in sorted(set(fa) - set(fb)):
        print(f'  ONLY-DEPLOYED {dm.get(n, n)[:150]}')
    for n in sorted(set(fb) - set(fa)):
        print(f'  ONLY-REBUILT {dm.get(n, n)[:150]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
