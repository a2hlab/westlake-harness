#!/usr/bin/env python3
"""Prepare a fresh runtime reproduction without changing historical sources or objects.

Only output/object locations are rewritten. All compile flags and source paths come
from the retained U13 recipe, six Emboss argv and n2/n4 GL build scripts. The n2
forwarder is regenerated, compared, then compiled at its historical source path
so debug path changes cannot be confused with a source revision.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(w, dest):
    w, dest = Path(w).resolve(), Path(dest).resolve()
    if dest.exists():
        raise ValueError('refuse reused build directory: ' + str(dest))
    b = w / 'westlake-harness-bms-deploy'
    p = w / 'westlake-inputs/generations/u13-runtime-m1-v1/build/u13'
    paths = {'recipe': p/'recipe.sh', 'driver': p/'driver.sh', 'emboss': p/'extra-commands.json',
             'n2': b/'benchmark/2026-09-30-n2-native/build-globjects.sh',
             'n4': b/'benchmark/2026-09-30-n4-native/build-egl.sh',
             'publication': b/'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp'}
    expected = {'recipe': 'f0c07e1a873506cfebe6ebf9038393b774e92f60f6eaa97e86b184c30c4f0130',
                'driver': 'cc19bab6d7759e854c9d132182f61b541c9eddb17d8ff5a3f001b36e521431e7',
                'emboss': '556b76fb6bfb5affd6a30ecbba9ebf86627f05dd567afc4e407ae7cb3047366a',
                'publication': 'ba5a3fe23d4a72f0406427e38b51259cc7c8fd0d04a7c78237d9f6d3fccac210'}
    for k, h in expected.items():
        if sha(paths[k]) != h:
            raise ValueError('historical input drift: ' + k)
    dest.mkdir(parents=True)
    pins = [{'role': k, 'path': str(v), 'sha256': sha(v)} for k,v in paths.items()]
    for group in ('n2', 'n4'):
        src = paths[group].read_text()
        src = src.replace('HERE=$(cd "$(dirname "$0")" && pwd)', f'HERE={shlex.quote(str(paths[group].parent))}')
        old = b / f'bms/src/.work/{group}-native/gl'
        src = src.replace(f'OUT=$REPO/bms/src/.work/{group}-native/gl', f'OUT={shlex.quote(str(dest/group))}')
        # Keep historical header include spelling; new include symlinks are local only.
        src = src.replace('-I$OUT/include)', f'-I{old}/include)')
        if group == 'n2':
            src = src.replace('"$TC/bin/clang-15" "${FLAGS[@]}" -c "$OUT/gl_forwarders.c"',
                f'cmp "$OUT/gl_forwarders.c" {shlex.quote(str(old / "gl_forwarders.c"))}\n"$TC/bin/clang-15" "${{FLAGS[@]}}" -c {shlex.quote(str(old / "gl_forwarders.c"))}')
            src = src.replace('> "$HERE/gl-identities.txt"', '> "$OUT/gl-identities.txt"')
        else:
            src = src.replace('> "$HERE/egl-object.txt"', '> "$OUT/egl-object.txt"')
        (dest/f'{group}.sh').write_text(src)
    recipe = paths['recipe'].read_text()
    for name in ('runtime-out', 'runtime-objects'):
        recipe = recipe.replace(str(p/name), str(dest/name))
    for group, names in {'n4': ['EGLImpl.o'], 'n2': ['GLImpl.o','forwarders.o','bounds.o']}.items():
        for name in names:
            recipe = recipe.replace(str(b/f'bms/src/.work/{group}-native/gl'/name), str(dest/group/name))
    (dest/'recipe.sh').write_text(recipe)
    driver = paths['driver'].read_text()
    for name in ('runtime-out', 'runtime-objects', 'recipe.sh'):
        driver = driver.replace(str(p/name), str(dest/name))
    driver = driver.replace('export BUILD_INNER_INVOKED=1', 'export BUILD_INNER_INVOKED=1\nexport N3B_WITH_PUBLICATION=1\nexport N3B_SOURCE=' + shlex.quote(str(paths['publication'])))
    (dest/'driver.sh').write_text(driver)
    commands = json.loads(paths['emboss'].read_text())
    emboss = ['#!/usr/bin/env bash','set -euo pipefail', 'mkdir -p '+shlex.quote(str(dest/'runtime-objects'))]
    for argv in commands:
        argv = [arg.replace(str(p/'runtime-objects'), str(dest/'runtime-objects')) for arg in argv]
        emboss.append(shlex.join(argv))
    (dest/'emboss.sh').write_text('\n'.join(emboss)+'\n')
    tc = b/'bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain'
    runner = ['#!/usr/bin/env bash','set -euo pipefail', 'cd '+shlex.quote(str(b)),
              'export LD_LIBRARY_PATH='+shlex.quote(str(tc/'runtime')),
              'bash '+shlex.quote(str(dest/'n2.sh')), 'bash '+shlex.quote(str(dest/'n4.sh')),
              'bash '+shlex.quote(str(dest/'emboss.sh')), 'bash -x '+shlex.quote(str(dest/'driver.sh'))]
    (dest/'run.sh').write_text('\n'.join(runner)+'\n')
    (dest/'preparation.json').write_text(json.dumps({'schema':1,'clean':True,'historical_inputs':pins,
        'publication_enabled':True,'external_objects_rebuilt':10,'reuses_historical_objects':False,
        'source_flags_edited':False,'generated_scripts':[{'path':str(x),'sha256':sha(x)} for x in dest.glob('*.sh')]},indent=2)+'\n')
    return dest


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--workspaces', default=os.environ.get('WORKSPACES'))
    ap.add_argument('--out', required=True)
    a=ap.parse_args()
    if not a.workspaces:
        ap.error('WORKSPACES or --workspaces required')
    print(prepare(a.workspaces, a.out))
