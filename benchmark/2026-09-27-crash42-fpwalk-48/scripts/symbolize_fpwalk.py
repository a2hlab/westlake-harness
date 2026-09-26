#!/usr/bin/env python3
"""Offline symbolizer for crash42 v2 AS-safe FP walk (#48 path A).

In-signal the recorder writes only RAW addresses (fp_frame_return[], pc) plus a /proc/self/maps
dump per event (async-signal-safe; no dl_iterate_phdr in signal context). This script resolves each
raw address to <lib> + <ELF file offset> using that event's maps file, so it can be fed straight to
llvm-objdump --start-address / addr2line against the on-VM ELF.

Usage:  symbolize_fpwalk.py <event.txt> [<event.maps>]
        (if maps path omitted, uses the sibling <event>.maps)

maps line: START-END perms FILEOFF dev inode  PATHNAME
For addr in a region:  elf_file_offset = FILEOFF + (addr - START)   (what objdump wants)
        load_base = min START over that pathname's r-x/executable mappings (addr - load_base = vaddr)
"""
import sys, re, pathlib

def parse_maps(text):
    regions = []            # (start, end, perms, fileoff, path)
    base_by_path = {}       # path -> min start (load base)
    for ln in text.splitlines():
        m = re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+(\S+)\s+([0-9a-f]+)\s+\S+\s+\d+\s*(.*)$', ln)
        if not m:
            continue
        start, end, perms, fileoff, path = int(m[1],16), int(m[2],16), m[3], int(m[4],16), m[5].strip()
        regions.append((start, end, perms, fileoff, path))
        if path:
            base_by_path[path] = min(base_by_path.get(path, start), start)
    return regions, base_by_path

def resolve(addr, regions, base_by_path):
    for start, end, perms, fileoff, path in regions:
        if start <= addr < end:
            elf_off = fileoff + (addr - start)
            name = path or "[anon]"
            lb = base_by_path.get(path)
            vaddr = (addr - lb) if lb is not None else None
            return name, elf_off, vaddr, perms
    return None, None, None, None

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    txt = pathlib.Path(sys.argv[1])
    maps = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else txt.with_suffix('.maps')
    if not maps.exists():
        sys.exit("maps file not found: %s" % maps)
    regions, base_by_path = parse_maps(maps.read_text(errors='replace'))
    pc = None; returns = []
    for ln in txt.read_text(errors='replace').splitlines():
        if not ln.startswith('[CRASH42] '):
            continue
        body = ln[len('[CRASH42] '):]
        if '=' not in body:
            continue
        k, v = body.split('=', 1)
        try: val = int(v, 16)
        except ValueError: continue
        if k == 'pc': pc = val
        elif k == 'fp_frame_return': returns.append(val)
    def line(tag, addr):
        name, elf_off, vaddr, perms = resolve(addr, regions, base_by_path)
        if name is None:
            return "%-16s 0x%016x  -> (unmapped)" % (tag, addr)
        vs = ("vaddr=0x%x " % vaddr) if vaddr is not None else ""
        return "%-16s 0x%016x  -> %s  elf_off=0x%x  %s(%s)" % (tag, addr, name, elf_off, vs, perms)
    print("== crash42 v2 fp-walk offline symbolization ==")
    print("event: %s   maps: %s   (%d regions)" % (txt.name, maps.name, len(regions)))
    if pc is not None: print(line("pc", pc))
    for i, r in enumerate(returns):
        print(line("fp_ret[%d]" % i, r))
    if not returns:
        print("(no fp_frame_return entries — check the handler ran and stack_vma was found)")

if __name__ == '__main__':
    main()
