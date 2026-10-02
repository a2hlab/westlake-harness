#!/usr/bin/env python3
"""Every library-open site in the host and child binaries, and which namespace each one opens into -- before the board.

    open_site_scan.py <elf> [<elf> ...] [--owners libx.so ...] [--json out.json] [--strict]
    open_site_scan.py --u9 [--owners ...]           # the signed U9 appspawn-x + child

Per site: function, PC, callee (dlopen / dlopen_ns / android_dlopen_ext / dlmopen, `b` tail calls included), the
namespace argument, the path (resolved C-string literals where adrp+add / csel reach them), the flags. Then:
  DEFAULT-NS   a plain dlopen / android_dlopen_ext / tail call -- opens into the caller's (often default) namespace;
  MULTI-NS     one library reaches sites with different namespace arguments -- each namespace maps its own copy;
  UNRESOLVED   path or namespace comes from a register / param / table -- static resolution stops here, read it.
--owners adds "may open" for an unresolved-path site in a binary that carries the owner's name string.

2026-10-02: the white-window double bridge/runtime copy cost two board rounds (N11f child r1, N11g child r2, each
build + window + rollback) and two wrong outer attributions ("host default dlopen"). The answer was static: the
deployed U9 appspawn-x has six open sites, all dlopen_ns into bridge/app namespaces that are not the child's
westlake.sealed.child -- two namespaces, two copies. One full open-site listing on day one skips both rounds.
Static-first rule: AGENTS.md B10. The linear backward scan ignores branch structure; csel is the only join it merges.
"""
import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

U9_GENERATION = 'westlake-generation-u9-j10g-238ffc14'
U9_BINARIES = ('native/payload/runtime/appspawn-x', 'native/payload/runtime/libwestlake_android_child.z.so')
# callee -> (namespace arg, path arg, flags arg); None = no namespace argument
OPEN_FUNCS = {
    'dlopen': (None, 0, 1),
    '__loader_dlopen': (None, 0, 1),
    'android_dlopen_ext': ('extinfo', 0, 1),
    '__loader_android_dlopen_ext': ('extinfo', 0, 1),
    'dlopen_ns': (0, 1, 2),
    'dlmopen': (0, 1, 2),
}
FLAG_BITS = [(0x1, 'LAZY'), (0x2, 'NOW'), (0x4, 'NOLOAD'), (0x100, 'GLOBAL'), (0x1000, 'NODELETE')]  # OH musl values
NON_DEF = re.compile(r'^(st|cmp|cmn|tst|cb|tb|b\.|b$|bl$|blr$|br$|ret|nop|prfm|dmb|dsb|isb|hint|bti|paciasp|autiasp)')
MAX_BACK = 4000  # to the function start: namespace registers are often set hundreds of instructions earlier


def epilogue_restore(mnem, ops):
    """`ldp x2N, x2M, [sp...]` into callee-saved registers restores the caller's values on an early-return path; a
    linear backward scan crossing it must not take it as the definition seen at a later call site."""
    if not mnem.startswith('ldp') or len(ops) < 3 or not ops[2].startswith('[sp'):
        return False
    regs = [reg_no(ops[0]), reg_no(ops[1])]
    return all(r is not None and r >= 19 for r in regs)


def tool(name):
    tools = sorted((Path.home() / 'Library/Android/sdk/ndk').glob(f'*/toolchains/llvm/prebuilt/*/bin/{name}'))
    return str(tools[-1]) if tools else name


def reg_no(token):
    m = re.fullmatch(r'[xw](\d+)', token.strip())
    return int(m.group(1)) if m else None


def split_ops(text):
    """Split an operand list on commas outside [] (so '[sp, #16]' stays one operand); drop the '<sym>' annotation."""
    text = re.sub(r'\s*<[^>]*>', '', text)
    out, depth, cur = [], 0, ''
    for c in text:
        depth += c == '['
        depth -= c == ']'
        if c == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += c
    return [x for x in (out + [cur.strip()]) if x]


def parse_disassembly(text):
    """objdump -d text -> {function: [(pc, mnemonic, operand_text)]}."""
    funcs, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'^([0-9a-f]+) <(.+)>:$', line)
        if m:
            cur = m.group(2)
            funcs[cur] = []
            continue
        parts = line.split('\t')
        if cur is None or len(parts) < 2:
            continue
        am = re.match(r'^\s*([0-9a-f]+):', parts[0])
        if am:
            funcs[cur].append((int(am.group(1), 16), parts[1].strip(), parts[2].strip() if len(parts) > 2 else ''))
    return funcs


class Elf:
    """Read-only: PT_LOAD virtual address -> file bytes, and the symbol table for naming globals."""

    def __init__(self, path):
        self.path, self.data = Path(path), Path(path).read_bytes()
        phoff, = struct.unpack_from('<Q', self.data, 0x20)
        phentsize, phnum = struct.unpack_from('<HH', self.data, 0x36)
        self.loads = []
        for i in range(phnum):
            p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from('<IIQQQQQQ', self.data, phoff + i * phentsize)
            if p_type == 1:
                self.loads.append((p_vaddr, p_offset, p_filesz))
        out = subprocess.run([tool('llvm-nm'), '-n', '--defined-only', '-S', str(path)], capture_output=True, text=True).stdout
        self.symbols = []
        for line in out.splitlines():
            f = line.split()
            if len(f) >= 4 and re.fullmatch(r'[0-9a-f]+', f[0]) and re.fullmatch(r'[0-9a-f]+', f[1]):
                self.symbols.append((int(f[0], 16), int(f[1], 16), f[3]))

    def cstring(self, va):
        for vaddr, offset, filesz in self.loads:
            if vaddr <= va < vaddr + filesz:
                start = offset + (va - vaddr)
                end = self.data.find(b'\0', start, start + 512)
                raw = self.data[start:end if end >= 0 else start]
                if raw and all(32 <= b < 127 for b in raw):
                    return raw.decode()
        return None

    def symbol(self, va):
        for addr, size, name in self.symbols:
            if addr <= va < addr + max(size, 1):
                return name if va == addr else f'{name}+{va - addr:#x}'
        return None

    def has_string(self, s):
        return s.encode() + b'\0' in self.data


def resolve(insns, idx, reg, elf, depth=0):
    """Values reaching register `reg` at insns[idx], by a linear backward scan of the function. Returns a list of
    ('lit', str) | ('addr', int) | ('imm', int) | ('stack', str) | ('param', str) | ('ret', callee) | ('unknown', why)."""
    if depth > 6:
        return [('unknown', 'resolution depth')]
    for j in range(idx - 1, max(-1, idx - 1 - MAX_BACK), -1):
        pc, mnem, ops_text = insns[j]
        ops = split_ops(ops_text)
        if mnem in ('bl', 'blr'):
            if reg == 0:
                return [('ret', re.sub(r'@plt$', '', (re.search(r'<([^>+]+)', ops_text) or re.search(r'(\S+)', ops_text)).group(1)))]
            if reg <= 18:
                return [('unknown', f'x{reg} clobbered by call at {pc:#x}')]
            continue
        if not ops or NON_DEF.match(mnem) or epilogue_restore(mnem, ops):
            continue
        dests = [reg_no(ops[0])] + ([reg_no(ops[1])] if mnem.startswith('ldp') and len(ops) > 1 else [])
        if reg not in dests:
            continue
        if mnem == 'mov' and len(ops) == 2:
            src = reg_no(ops[1])
            if src is not None:
                return resolve(insns, j, src, elf, depth + 1)
            if ops[1].startswith('#'):
                return [('imm', int(ops[1][1:], 0))]
            if ops[1] in ('sp',):
                return [('stack', 'sp')]
            return [('unknown', f'{mnem} {ops_text}')]
        if mnem in ('movz',) and ops[1].startswith('#'):
            return [('imm', int(ops[1][1:].split()[0], 0))]
        if mnem == 'adrp':
            return [('addr', int(ops[1], 0))]
        if mnem == 'add' and len(ops) == 3 and ops[2].startswith('#'):
            imm = int(ops[2][1:].split()[0], 0)
            if ops[1] == 'sp':
                return [('stack', f'sp+{imm:#x}')]
            base = reg_no(ops[1])
            vals = resolve(insns, j, base, elf, depth + 1) if base is not None else [('unknown', ops_text)]
            out = []
            for kind, v in vals:
                if kind == 'addr':
                    s = elf.cstring(v + imm) if elf else None
                    out.append(('lit', s) if s else ('addr', v + imm))
                else:
                    out.append((kind, v))
            return out
        if mnem == 'csel' and len(ops) >= 3:
            out = []
            for src in ops[1:3]:
                n = reg_no(src)
                out += resolve(insns, j, n, elf, depth + 1) if n is not None else [('unknown', src)]
            return out
        if mnem.startswith('ldr') and len(ops) >= 2 and re.match(r'\[(sp|x29)\b', ops[1]):
            return [('stack', f'frame slot {ops[1]}')]
        return [('unknown', f'{mnem} {ops_text}')]
    return [('param', f'x{reg}')] if reg <= 7 else [('unknown', f'x{reg} live-in')]


def render(vals, elf=None):
    out = []
    for kind, v in vals:
        if kind == 'lit':
            out.append(v)
        elif kind == 'addr':
            sym = elf.symbol(v) if elf else None
            out.append(f'global:{sym}' if sym else f'addr:{v:#x}')
        elif kind == 'imm':
            out.append(f'#{v:#x}')
        else:
            out.append(f'{kind}:{v}')
    return out


def decode_flags(vals):
    imms = [v for k, v in vals if k == 'imm']
    if len(imms) != 1:
        return render(vals)
    if not 0 <= imms[0] <= 0x1fff:  # not a flag word: the linear scan reached a def on another path
        return [f'#{imms[0]:#x}?']
    names = [n for bit, n in FLAG_BITS if imms[0] & bit]
    return [f'{imms[0]:#x}=' + ('|'.join(names) or 'LOCAL')]


def scan(path, disassembly=None, elf=None):
    elf = elf or Elf(path)
    text = disassembly if disassembly is not None else subprocess.run(
        [tool('llvm-objdump'), '-d', str(path)], capture_output=True, text=True).stdout
    sites = []
    for func, insns in parse_disassembly(text).items():
        for i, (pc, mnem, ops_text) in enumerate(insns):
            m = re.search(r'<([\w.$]+)@plt>', ops_text)
            if mnem not in ('bl', 'b') or not m or m.group(1) not in OPEN_FUNCS:
                continue
            callee = m.group(1)
            ns_arg, path_arg, flags_arg = OPEN_FUNCS[callee]
            ns = ['caller-default'] if ns_arg is None else (
                ['extinfo:' + ','.join(render(resolve(insns, i, 2, elf), elf))] if ns_arg == 'extinfo'
                else render(resolve(insns, i, ns_arg, elf), elf))
            sites.append({'binary': Path(path).name, 'function': func, 'pc': f'{pc:#x}', 'callee': callee,
                          'tail_call': mnem == 'b', 'namespace': ns,
                          'path': render(resolve(insns, i, path_arg, elf), elf),
                          'flags': decode_flags(resolve(insns, i, flags_arg, elf))})
    return sites, elf


def findings(results, owners):
    """results: [(path, sites, elf)] -> list of finding dicts."""
    out, by_lib = [], {}
    for _, sites, elf in results:
        for s in sites:
            key = f"{s['binary']}:{s['function']}@{s['pc']}"
            if s['namespace'] == ['caller-default'] or s['tail_call']:
                out.append({'kind': 'DEFAULT-NS', 'site': key, 'callee': s['callee'], 'path': s['path'],
                            'tail_call': s['tail_call']})
            if any('NOLOAD' in f for f in s['flags']):
                continue  # a NOLOAD lookup finds an existing mapping; it never creates a copy
            libs = [Path(p).name for p in s['path'] if p.startswith('/') or p.endswith('.so')]
            if not libs:
                out.append({'kind': 'UNRESOLVED', 'site': key, 'path': s['path'], 'namespace': s['namespace']})
                libs = [o for o in owners if elf.has_string(o) or elf.has_string('/system/android/lib64/' + o)]
                how = 'may'
            else:
                how = 'resolved'
            for lib in libs:
                by_lib.setdefault(lib, []).append({'site': key, 'namespace': ' | '.join(s['namespace']), 'how': how})
    for lib, reaches in sorted(by_lib.items()):
        resolved = {r['namespace'] for r in reaches if r['how'] == 'resolved'}
        if len(resolved) > 1:
            out.append({'kind': 'MULTI-NS', 'confidence': 'confirmed', 'library': lib, 'owner': lib in owners,
                        'reaches': reaches})
        elif len({r['namespace'] for r in reaches}) > 1:
            out.append({'kind': 'MULTI-NS', 'confidence': 'possible', 'library': lib, 'owner': lib in owners,
                        'reaches': reaches})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('elf', nargs='*')
    ap.add_argument('--u9', action='store_true', help=f'scan the signed U9 host + child in $WORKSPACES/{U9_GENERATION}')
    ap.add_argument('--owners', nargs='*', default=['liboh_adapter_bridge.so', 'liboh_android_runtime.so'])
    ap.add_argument('--json', help='write sites + findings here')
    ap.add_argument('--strict', action='store_true', help='exit 1 when an owner library reaches two namespaces')
    args = ap.parse_args()
    paths = list(args.elf) + ([str(lab_paths.workspaces() / U9_GENERATION / b) for b in U9_BINARIES] if args.u9 else [])
    if not paths:
        ap.error('give ELF paths or --u9')
    results = []
    for p in paths:
        sites, elf = scan(p)
        results.append((p, sites, elf))
        print(f'== {p}  ({len(sites)} open sites)')
        for s in sites:
            tail = ' TAIL' if s['tail_call'] else ''
            print(f"   {s['function']}@{s['pc']} {s['callee']}{tail}  ns={' | '.join(s['namespace'])}  "
                  f"path={' | '.join(s['path'])}  flags={' | '.join(s['flags'])}")
    found = findings(results, args.owners)
    print('== findings')
    for f in found:
        if f['kind'] == 'MULTI-NS':
            print(f"   MULTI-NS {f['confidence']} {f['library']}{' (owner)' if f['owner'] else ''}:")
            for r in f['reaches']:
                print(f"      {r['how']:8} {r['site']}  ns={r['namespace']}")
        else:
            print(f"   {f['kind']} {f['site']}  " + json.dumps({k: v for k, v in f.items() if k not in ('kind', 'site')},
                                                         ensure_ascii=False))
    if args.json:
        Path(args.json).write_text(json.dumps({'binaries': [{'path': p, 'sites': s} for p, s, _ in results],
                                               'findings': found}, ensure_ascii=False, indent=1) + '\n')
    return 1 if args.strict and any(f['kind'] == 'MULTI-NS' and f['owner'] and f['confidence'] == 'confirmed'
                                    for f in found) else 0


if __name__ == '__main__':
    sys.exit(main())
