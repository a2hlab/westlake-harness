"""Minimal VM-only diagnostic relink: one sigchain object plus recorder object.

First reproduce the frozen baseline byte-for-byte. Never writes shared outputs.
The resulting libart is diagnostic, not approved for deployment by this script.
"""
import hashlib
import json
import pathlib
import subprocess

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ws = pathlib.Path.home()/'a2hlab/ws'
    root = ws/'out-crash42/recorder'
    output = root/'art'
    output.mkdir(exist_ok=False)
    original = ws/'out/art/runtime'
    baseline = original/'libart.so'
    expected = '009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc'
    assert sha(baseline) == expected, 'Baseline differs from #42'
    report = json.loads((original/'artifacts.json').read_text())
    objects = ws/'out/art/objects'
    inputs = []
    # artifacts.json is sorted; retain link ordering from the original make target.
    core = subprocess.check_output(['make', '--no-print-directory', '-s', '-C', str(ws/'art-build'),
        '-f', 'Makefile.ohos-arm64', 'WORKSPACE='+str(ws), 'BUILDDIR='+str(objects),
        'print-clean-core-objects'], text=True).splitlines()
    additional = ['stubs/nterp_real_port.o', 'sigchain/sigchain.o',
        'stubs/link_stubs_arm64.weak.o', 'stubs/code_generator_vector_arm64_sve_stub.o',
        'stubs/fault_handler_stubs.o', 'stubs/template_instantiations.weak.o',
        'stubs/metrics_stubs.weak.o', 'stubs/thread_cpu_stub.weak.o',
        'stubs/openjdkjvm_runtime_services.weak.o', 'fmtlib/format.o', 'tinyxml2/tinyxml2.o',
        'asm_arm64/quick_entrypoints_arm64.o', 'asm_arm64/jni_entrypoints_arm64.o',
        'asm_arm64/memcmp16_arm64.o', 'asm_arm64/mterp_arm64ng.o']
    inputs = [pathlib.Path(p) for p in core]+[objects/p for p in additional]
    assert len(inputs) == len(set(inputs)) == len(report['objects'])
    for p in inputs:
        assert sha(p) == report['objects'][str(p.relative_to(objects))], p
    sdk = ws/'toolchains/ohos-sdk/native'
    compiler = sdk/'llvm/bin/clang++'
    flags = ['--target=aarch64-linux-ohos', '--sysroot='+str(sdk/'sysroot'), '-fPIC', '-O2',
             '-shared', '-fuse-ld=lld', '-nostdlib++', '-Wl,-Bsymbolic', '-Wl,--build-id=sha1',
             '-Wl,--version-script='+str(ws/'art-build/ziparchive_hide.map'),
             '-Wl,-soname,libart.so', '-Wl,--allow-shlib-undefined']
    boundary = original/'libwestlake_runtime_boundary.so'
    libcxx = ws/'toolchains/clang-15/lib/aarch64-linux-ohos/libc++.so'
    zlib = original/'libz.so'
    for p in (boundary, zlib): assert sha(p) == report['artifacts'][p.name]['sha256'], p
    assert sha(libcxx) == report['platform_providers']['libc++.so']['sha256']
    def link(path, selected):
        cmd = [compiler, *flags, '-o', path, *selected, '-Wl,--no-as-needed', boundary,
               libcxx, '-Wl,--as-needed', zlib, '-lc', '-ldl', '-lpthread']
        subprocess.run(list(map(str, cmd)), check=True)
    reproduced = output/'baseline-relinked.so'
    link(reproduced, inputs)
    assert sha(reproduced) == expected, 'Baseline relink not identical; do not produce candidate'
    source = root/'sigchain_musl_diag.cc'
    native = pathlib.Path(__file__).resolve().parents[1]/'native'
    obj = output/'sigchain.o'
    subprocess.run(list(map(str, [compiler, '--target=aarch64-linux-ohos',
        '--sysroot='+str(sdk/'sysroot'), '-std=c++17', '-O2', '-g', '-fPIC',
        '-Wall', '-Wextra', '-Werror', '-I'+str(native), '-c', source, '-o', obj])), check=True)
    selected = [obj if p == objects/'sigchain/sigchain.o' else p for p in inputs]
    selected.append(root/'crash_snapshot.o')
    candidate = output/'libart.so'; link(candidate, selected)
    record = dict(baseline_sha256=expected, reproduced_sha256=sha(reproduced),
                  candidate_sha256=sha(candidate), objects_verified=len(inputs),
                  replaced='sigchain/sigchain.o', added='crash_snapshot.o',
                  device_verified=False, full_stack_unwind_verified=False)
    (output/'relink.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))

if __name__ == '__main__': main()
