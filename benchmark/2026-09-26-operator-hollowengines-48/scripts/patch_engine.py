import sys, struct
path, kind = sys.argv[1], sys.argv[2]
MOV1_RET = bytes.fromhex('200080d2' 'c0035fd6')  # little-endian: d2800020, d65f03c0 -> mov x0,#1; ret
MOV0_RET = bytes.fromhex('000080d2' 'c0035fd6')  # d2800000, d65f03c0 -> mov x0,#0; ret
# (vaddr == file offset in .text for these libs)
targets = {
 'bytehook': [(0x0dcd4,'install','bytehook_hook_single'),(0x0dce8,'install','bytehook_hook_partial'),
              (0x0dcfc,'install','bytehook_hook_all'),(0x0dd10,'unhook','bytehook_unhook')],
 'shadowhook': [(0x0c5d4,'install','shadowhook_hook_func_addr'),(0x0c764,'install','shadowhook_hook_sym_addr'),
                (0x0c77c,'install','shadowhook_hook_sym_name'),(0x0c924,'install','shadowhook_hook_sym_name_callback'),
                (0x0c938,'unhook','shadowhook_unhook')],
}[kind]
data=bytearray(open(path,'rb').read())
for off,typ,name in targets:
    orig=bytes(data[off:off+8])
    patch = MOV1_RET if typ=='install' else MOV0_RET
    data[off:off+8]=patch
    print(f"  {name:38s} @0x{off:05x}  {orig.hex()} -> {patch.hex()}  [{typ}]")
open(path,'wb').write(data)
print("  wrote", path)
