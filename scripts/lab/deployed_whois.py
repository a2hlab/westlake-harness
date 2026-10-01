#!/usr/bin/env python3
"""Which copy of a library / class is actually deployed and loaded -- answer this before changing or judging it.

    deployed_whois.py libandroid.so                     # every deployed copy: path, sha, SONAME, NEEDED; U9 maps hits
    deployed_whois.py Ladapter/activity/WifiFetcher;    # which deployed JARs define the class
    deployed_whois.py --generation <dir> ...            # another generation instead of the signed U9 one

retro 21 (2026-10-01): three outer R2s in one hour reasoned from a proxy instead of the deployed object --
  * the ANativeWindow lock design targeted "our libandroid (hwui-shim sources)", but the libandroid.so apps map is a
    renamed old liboh_android_runtime (SONAME liboh_android_runtime.so, 9ccf64f8), and a private copy already had lock;
  * "wifi / media_session come back null" was read off the vm-copies source snapshot, while the deployed JAR 238ffc14
    has WifiFetcher and [B8-FETCH] media_session;
  * U10ShareResidentCompat was validated on an offline AOSP-semantics mock against a board-proven OH musl behaviour.
The deployed generation and the signed run's maps are on this Mac; this prints them in one go.
"""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lab_paths  # noqa: E402

SIGNOFF = REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json'
DEFAULT_GENERATION = 'westlake-generation-u9-j10g-238ffc14'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def readelf():
    tools = sorted((Path.home() / 'Library/Android/sdk/ndk').glob('*/toolchains/llvm/prebuilt/*/bin/llvm-readelf'))
    return str(tools[-1]) if tools else 'llvm-readelf'


def elf_facts(path):
    out = subprocess.run([readelf(), '-d', str(path)], capture_output=True, text=True).stdout
    soname = re.findall(r'\(SONAME\)\s+Library soname: \[(.+?)\]', out)
    needed = re.findall(r'\(NEEDED\)\s+Shared library: \[(.+?)\]', out)
    return (soname[0] if soname else '-'), needed


def signed_run_dirs():
    if not SIGNOFF.exists():
        return []
    ws = str(lab_paths.workspaces())
    runs = json.loads(SIGNOFF.read_text()).get('runs') or {}
    return [Path(p.replace('$WORKSPACES', ws)).parent for p in runs.values()]


def library(name, generation):
    print(f'== deployed copies of {name} in {generation.name}')
    copies = sorted(p for p in generation.rglob(name) if p.is_file())
    if not copies:
        print('   none')
    for p in copies:
        soname, needed = elf_facts(p)
        flag = '' if soname in (name, '-') else f'   <-- SONAME differs from the file name'
        print(f'   {p.relative_to(generation)}  sha {sha(p)}  SONAME {soname}  NEEDED {",".join(needed) or "-"}{flag}')
    hits = collections.Counter()
    maps = 0
    for run in signed_run_dirs():
        for f in run.glob('*/maps-t5-*.txt'):
            maps += 1
            for line in set(l.split()[-1] for l in f.read_text(errors='replace').splitlines() if l.strip()):
                if line.endswith('/' + name):
                    hits[line] += 1
    print(f'== {name} in the signed U9 run maps ({maps} maps files)')
    if not hits:
        print('   never mapped')
    for path, n in hits.most_common():
        print(f'   {path}  in {n} process(es)')


def klass(name, generation):
    needle = name.encode()
    print(f'== deployed JARs/DEX in {generation.name} that define or reference {name}')
    found = False
    for jar in sorted(generation.rglob('*.jar')):
        try:
            with zipfile.ZipFile(jar) as z:
                for entry in [n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]:
                    if needle in z.read(entry):
                        found = True
                        print(f'   {jar.relative_to(generation)}!{entry}  (jar sha {sha(jar)})')
        except zipfile.BadZipFile:
            continue
    if not found:
        print('   not present in any deployed dex string table')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('name', help='a library file name (libx.so) or a class descriptor (Lpkg/Name;)')
    ap.add_argument('--generation', help=f'generation directory (default $WORKSPACES/{DEFAULT_GENERATION})')
    args = ap.parse_args()
    generation = Path(args.generation) if args.generation else lab_paths.workspaces() / DEFAULT_GENERATION
    if not generation.is_dir():
        sys.exit(f'no generation directory {generation}')
    if args.name.startswith('L') and args.name.endswith(';'):
        klass(args.name, generation)
    else:
        library(args.name, generation)
    return 0


if __name__ == '__main__':
    sys.exit(main())
