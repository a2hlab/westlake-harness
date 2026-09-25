#!/usr/bin/env python3
"""Quote the lines #37 relies on, verbatim (HTML tags stripped; raw-file line numbers).
Reads ~/workspace/hanbin_adapter, the westlake/harness trees and the sibling Bridge tree; writes to stdout."""
import html, re
from pathlib import Path

HOME = Path.home()
H = HOME / 'workspace/hanbin_adapter'
VM = HOME / 'OrbStack/a2hlab/home/zhaoyue/a2hlab'
SOURCES = [
    ('hanbin: overwritten OH files', H / 'deploy/deploy_all_init.sh', list(range(66, 77))),
    ('hanbin: PT_INTERP set by patchelf', H / 'build/inner/zygote-x/compile_zygote_x.sh', [53, 54, 55, 56, 57, 183]),
    ('hanbin: Bionic/ART built with Soong', H / 'build/build_aosp_lib.sh', [260, 333]),
    ('hanbin: AOSP tag', H / 'build/inner/fetch_missing_aosp_projects.sh', [57]),
    ('hanbin: policy.31 brick, 2026-09-08', H / 'deploy/deploy_all_init.sh', list(range(1298, 1307))),
    ('hanbin: Mali blob single-instance loading is unverified', H / 'framework/zygote-x/config/ld.config.txt', [77, 78, 79, 80, 81]),
    ('hanbin: design (direction 2)', H / 'doc/design/app_fwk_bionic_design_v2.html', [243, 247, 431, 451, 472, 474]),
    ('westlake: parent launched from the hdc shell, child forked by appspawn-x', VM / 'manifest/tools/probe_source_app.py', [521, 525, 526, 527, 537]),
    ('board: / is read-only ext4, no dm device',
     VM / 'ws/westlake-applib23/evidence/app-lib-loading-23/scripts/baseline-mount-label.txt', [1]),
    ('board: permissive used for launches 3-7', HOME / 'orca/workspaces/westlake-harness/benchmark/2026-09-22-burgerking-blind/README.md', [55, 56, 57, 58]),
    ('hardware: one D600 flashed with Android as same-hardware control', HOME / 'orca/workspaces/westlake-inputs/HANDOFF.md', [7]),
    ('sibling Bridge project: remount / rw on D600/OH 6.1', HOME / 'orca/01.OH61AOSP16/docs/errors/appspawn-x-v2sig-wall-rootcause.md', [204, 205, 206]),
]


def text(line):
    return html.unescape(re.sub(r'<[^>]+>', '', line)).rstrip()


def main():
    print('# Lines quoted verbatim for board #37 (HTML tags stripped; raw-file line numbers). Read only.')
    for title, path, nums in SOURCES:
        print(f'\n## {title}\n# {path.relative_to(HOME)}')
        lines = path.read_text(encoding='utf-8', errors='replace').split('\n')
        for n in nums:
            body = text(lines[n - 1]).strip()
            if body:
                print(f'{n}: {body[:300]}')


if __name__ == '__main__':
    main()
