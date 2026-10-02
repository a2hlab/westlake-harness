#!/usr/bin/env python3
"""Every method and field of the deployed jar is unchanged (smali text) in the patched jar; report what was added.

    verify_identity.py <deployed.jar> <patched.jar>

Exit 1 when any deployed member differs or disappears, or a deployed class is missing. deployed_class_diff.py checks
class presence and shape (super / interfaces); this checks the member bodies the patch promised not to touch.
"""
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import merge_smali  # noqa: E402

TOOLS = Path.home() / 'orca/workspaces/westlake-inputs/tools'
CP = ':'.join(str(TOOLS / j) for j in ('baksmali-2.5.2.jar', 'dexlib2-2.5.2.jar', 'util-2.5.2.jar', 'guava-31.1-jre.jar',
                                         'jcommander-1.78.jar', 'failureaccess-1.0.1.jar', 'smali-2.5.2.jar'))


def smali(jar, out):
    with zipfile.ZipFile(jar) as z:
        (Path(out) / 'classes.dex').write_bytes(z.read('classes.dex'))
    subprocess.run(['java', '-cp', CP, 'org.jf.baksmali.Main', 'd', str(Path(out) / 'classes.dex'), '-o',
                    str(Path(out) / 'smali')], check=True)
    return merge_smali.load(Path(out) / 'smali')


def main():
    deployed_jar, patched_jar = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        base, new = smali(deployed_jar, a), smali(patched_jar, b)
        changed, members, added = [], 0, 0
        for cls, (_, text) in sorted(base.items()):
            if cls not in new:
                changed.append(f'{cls}: class missing')
                continue
            bm, bf = merge_smali.blocks(text)
            nm, nf = merge_smali.blocks(new[cls][1])
            for sig, block in list(bm.items()) + list(bf.items()):
                members += 1
                got = nm.get(sig) if sig in bm else nf.get(sig)
                if got is None or got.strip() != block.strip():
                    changed.append(f'{cls}->{sig}')
            added += len(set(nm) - set(bm)) + len(set(nf) - set(bf))
        print(f'{len(base)} deployed classes, {members} deployed members, {len(changed)} changed; '
              f'{added} member(s) added to deployed classes, {len(set(new) - set(base))} class(es) added')
        for c in changed:
            print('  CHANGED', c)
    return 1 if changed else 0


if __name__ == '__main__':
    sys.exit(main())
