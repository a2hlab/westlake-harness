#!/usr/bin/env python3
"""U13 runtime candidate = deployed ac59dec0 + M1 (android_graphics_compat_shim.o) + AssetManager lazy mObject
(asset_manager.o, cc-wiki aa149019). Replays the N10b smoke-markers recipe (build-runtime.py) on a2hlab.

    WORKSPACES=<...> python3 build_runtime_u13.py      # run on the a2hlab VM (x86_64 frozen toolchain)

Variants, each a fresh copy of .work/n4-registration-order/runtime-objects linked by the recipe:
  baseline    the N10b baseline recipe                                   -> must equal U8 216b68fb
  control     N10b candidate recipe, compat_shim.o + asset_manager.o deleted and recompiled from their
              ORIGINAL sources (N2 b94f69e4 / aosp_raw asset_manager)    -> must equal deployed ac59dec0
  m1          control with the compat shim source replaced by runtime/src (M1 patch)
  u13         m1 + asset_manager.cpp patched with ../../2026-10-02-getlongfield-null/patch/asset_manager.cpp.patch
  u13-repeat  same as u13                                                -> must equal u13
Sources are substituted by path in the recipe text; nothing in the shared .work tree is edited. Every variant's
driver output goes to <out>/<variant>/build.log as it runs (the caller tees the session log too).
Writes runtime-build-receipt-u13.json next to this script.
"""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
REPO = H.parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
SM = REPO / 'benchmark/2026-10-01-n10b-child/smoke-markers'
D = WS / 'westlake-harness-bms-deploy'
W = D / 'bms/src/.work'
OLD = W / 'n4-registration-order'
F = W / 'product-tls-generation/frozen'
ADAPTER_ROOT = W / 'b87-native/adapter'
N2_SHIM = D / 'benchmark/2026-09-30-n2-native/src/android_graphics_compat_shim.cpp'
AM_REL = 'third_party/aosp_raw/frameworks/base/native/android/asset_manager.cpp'
AM_PATCH = REPO / 'benchmark/2026-10-02-getlongfield-null/patch/asset_manager.cpp.patch'
M1_SHIM = H / 'src/android_graphics_compat_shim.cpp'
OUT = Path(os.environ.get('U13_RUNTIME_OUT', str(lab_paths.inputs() / 'generations/u13-runtime-m1-v1/build')))
DEPLOYED = 'ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert sha(N2_SHIM).startswith('b94f69e4'), 'N2 compat shim source drifted'
    recipe0 = (OLD / 'recipe.sh').read_text()
    driver0 = (OLD / 'driver.sh').read_text()
    assert str(N2_SHIM) in recipe0 and '$ADAPTER_ROOT/' + AM_REL in recipe0
    baseline = json.loads((WS / 'westlake-generation-u8-j9-t7e/native/package.json').read_text())['files'][
        'payload/android/lib64/liboh_android_runtime.so']
    OUT.mkdir(parents=True, exist_ok=False)
    # patched asset_manager.cpp: a copy of the original with cc-wiki's patch applied (git apply), original untouched
    am_tree = OUT / 'src-asset-manager'
    am_dst = am_tree / 'frameworks/base/native/android/asset_manager.cpp'
    am_dst.parent.mkdir(parents=True)
    shutil.copy2(ADAPTER_ROOT / AM_REL, am_dst)
    subprocess.run(['git', 'init', '-q', str(am_tree)], check=True)
    subprocess.run(['git', '-C', str(am_tree), 'apply', str(AM_PATCH)], check=True)
    env = os.environ.copy()
    env.update(N3B_SOURCE=str(D / 'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp'),
               N3B_WITH_PUBLICATION='1', LD_LIBRARY_PATH=str(W / 'b6-art14-recovery/tools/lib64'))
    records = {'inputs': {'n2_shim': sha(N2_SHIM), 'm1_shim': sha(M1_SHIM),
                          'asset_manager_original': sha(ADAPTER_ROOT / AM_REL), 'asset_manager_patched': sha(am_dst),
                          'asset_manager_patch': sha(AM_PATCH), 'recipe_n4': sha(OLD / 'recipe.sh'),
                          'clang++': sha(F / 'toolchain/bin/clang++')}}
    for variant in ['baseline', 'control', 'm1', 'u13', 'u13-repeat']:
        out = OUT / variant
        out.mkdir()
        shutil.copytree(OLD / 'runtime-objects', out / 'runtime-objects')
        (out / 'runtime-out').mkdir()
        for p in (out / 'runtime-objects').glob('*.o'):
            p.touch()
        (out / 'runtime-objects/AndroidRuntime.o').unlink()
        recipe = recipe0
        commands = []
        if variant != 'baseline':
            (out / 'runtime-objects/android_graphics_Typeface.o').unlink()
            (out / 'runtime-objects/android_graphics_compat_shim.o').unlink()
            (out / 'runtime-objects/asset_manager.o').unlink()
            recipe = recipe.replace(str(D / 'benchmark/2026-10-01-j6-n4-sweep/n4-registration-order/AndroidRuntime.cpp'),
                                    str(SM / 'src/AndroidRuntime.cpp'))
            recipe = recipe.replace('$SRC/src/android_graphics_Typeface.cpp', str(SM / 'src/android_graphics_Typeface.cpp'))
            recipe = recipe.replace('SRCS=(', 'SRCS=(\n    ' + shlex.quote(str(SM / 'src/asset-offsets-init.cpp')))
            if variant in ('m1', 'u13', 'u13-repeat'):
                recipe = recipe.replace(str(N2_SHIM), str(M1_SHIM))
            if variant in ('u13', 'u13-repeat'):
                recipe = recipe.replace('$ADAPTER_ROOT/' + AM_REL, str(am_dst))
            # the smoke-markers emboss objects + canvaskit link input, exactly as build-runtime.py
            src_line = [l for l in (SM / 'build-runtime.py').read_text().splitlines() if l.strip().startswith('cc=[')][0]
            cc = eval(src_line.strip()[3:], {'F': F, 'W': W, 'S': W / 'b68-generation/oh/third_party/skia/m133', 'str': str})
            objects = []
            for p in sorted((SM / 'src/emboss').glob('*.cpp')):
                o = out / 'runtime-objects' / ('n10b-' + p.stem + '.o')
                cmd = cc + ['-c', str(p), '-o', str(o)]
                commands.append(cmd)
                subprocess.run(cmd, check=True, env=env)
                objects.append(str(o))
            recipe = recipe.replace('if $CXX --target=aarch64-linux-ohos $LDFLAGS',
                                    'objs+=(' + ' '.join(shlex.quote(x) for x in objects) + ')\nif $CXX --target=aarch64-linux-ohos $LDFLAGS')
            recipe = recipe.replace('    -landroidfw -lbase', '    ' + shlex.quote(str(W / 'b11-egl-retry/link-inputs/libskia_canvaskit.z.so'))
                                    + ' \\\n    -landroidfw -lbase')
        (out / 'extra-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        (out / 'recipe.sh').write_text(recipe)
        (out / 'driver.sh').write_text(driver0.replace(str(OLD), str(out)))
        with (out / 'build.log').open('w') as f:
            subprocess.run(['bash', str(out / 'driver.sh')], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
        binary = out / 'runtime-out/liboh_android_runtime.so'
        records[variant] = {'sha256': sha(binary), 'objects': {p.name: sha(p) for p in (out / 'runtime-objects').glob('*.o')},
                            'recipe_sha256': sha(out / 'recipe.sh'), 'driver_sha256': sha(out / 'driver.sh'),
                            'build_log_sha256': sha(out / 'build.log')}
        print(variant, records[variant]['sha256'], flush=True)
    assert records['baseline']['sha256'] == baseline, ('baseline', records['baseline']['sha256'], baseline)
    assert records['control']['sha256'] == DEPLOYED, ('control != deployed ac59dec0', records['control']['sha256'])
    assert records['u13-repeat']['sha256'] == records['u13']['sha256'], 'u13 not deterministic'
    (H / 'runtime-build-receipt-u13.json').write_text(json.dumps(
        {'baseline_expected': baseline, 'deployed_expected': DEPLOYED, 'variants': records,
         'out_directory': str(OUT).replace(str(WS), '$WORKSPACES')}, indent=2) + '\n')
    print('u13 candidate', records['u13']['sha256'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
