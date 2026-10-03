#!/usr/bin/env python3
"""Build the window-7 pair on hw248 (2026-10-03-m2-a0-runtime-plan): worker libwl_a0_nweb.so (full NWeb body) and the
entry libwestlake_html_compat.so (JNI_OnLoad: default-inheriting ns + dlopen_ns worker + dlsym a0_probe_start).

    A0_BUILD=<dir> OH610=<tree> OH_SYSROOT=<sysroot> build_win7_hw248.sh <tag>

Same compiler/flags as the earlier builds (clang feef13a3, libcxx-ohos __h, -fno-rtti, -fvisibility=hidden,
--no-undefined, path prefix-maps). The worker links the full OH set (loaded in a default-inheriting ns, so all resolve).
The entry links only libhilog + libc and resolves musl dlns ops at run time via dlsym(RTLD_DEFAULT).
"""
import os, subprocess, sys
from pathlib import Path
B = Path(os.environ['A0_BUILD']); OH = Path(os.environ['OH610']); SYSROOT = os.environ['OH_SYSROOT']; TAG = sys.argv[1]
LLVM = OH / 'prebuilts/clang/ohos/linux-x86_64/llvm'; O = B / 'out' / TAG; O.mkdir(parents=True, exist_ok=True)
CXX = str(LLVM / 'bin/clang++')
common = ['--target=aarch64-linux-ohos', f'--sysroot={SYSROOT}', '-fPIC', '-O2', '-g', '-fstack-protector-strong',
          '-D__MUSL__', '-DOHOS_PLATFORM', '-Wno-c++11-narrowing', f'-ffile-prefix-map={B}=.', f'-ffile-prefix-map={OH}=OH',
          f'-ffile-prefix-map={SYSROOT}=SYSROOT']
inc = ['-I' + l for l in (B / 'out/include-dirs.txt').read_text().split()] + ['-I' + str(B / 'src/genstub')]

# worker: full NWeb body
subprocess.run([CXX, *common, '-std=c++17', '-fno-rtti', '-nostdinc++', '-isystem',
                str(LLVM / 'include/libcxx-ohos/include/c++/v1'), '-fvisibility=hidden', *inc,
                '-c', str(B / 'src/native/a0probe.cpp'), '-o', str(O / 'worker.o')], check=True)
subprocess.run([CXX, *common, '-shared', '-nostdlib++', '-fuse-ld=lld', '-Wl,--no-undefined', '-Wl,--build-id=sha1',
                '-Wl,-soname,libwl_a0_nweb.so', '-o', str(O / 'libwl_a0_nweb.so'), str(O / 'worker.o'), '-L' + str(B / 'lib'),
                '-l:libarkweb_core_loader.z.so', '-l:libapp_context.z.so', '-l:libappexecfwk_base.z.so',
                '-l:libeventhandler.z.so', '-l:libsurface.z.so', '-l:libsync_fence.z.so', '-l:libbegetutil.z.so',
                '-l:librender_service_client.z.so', '-l:libutils.z.so', '-l:libhilog.so', '-l:libc++.so'], check=True)

# entry: minimal (libhilog + libc); musl dlns ops resolved at run time
subprocess.run([CXX, *common, '-std=c++17', '-fno-rtti', '-nostdinc++', '-isystem',
                str(LLVM / 'include/libcxx-ohos/include/c++/v1'), '-fvisibility=hidden',
                '-c', str(B / 'src/native/a0_entry.cpp'), '-o', str(O / 'entry.o')], check=True)
subprocess.run([CXX, *common, '-shared', '-nostdlib++', '-fuse-ld=lld', '-Wl,--no-undefined', '-Wl,--build-id=sha1',
                '-Wl,-soname,libwestlake_html_compat.so', '-o', str(O / 'libwestlake_html_compat.so'), str(O / 'entry.o'),
                '-L' + str(B / 'lib'), '-l:libhilog.so'], check=True)
for so in ('libwl_a0_nweb.so', 'libwestlake_html_compat.so'):
    print(subprocess.run(['sha256sum', str(O / so)], capture_output=True, text=True).stdout.strip())
