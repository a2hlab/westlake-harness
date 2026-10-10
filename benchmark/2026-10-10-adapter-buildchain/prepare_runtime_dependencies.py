#!/usr/bin/env python3
"""Prepare dependency-only compiler invocations from the retained compile argv.

-M/-MF replace code generation; no original object or source is written. The
original stdout/stderr is captured by the invoking shell into a persistent log.
"""
import argparse
import json
from pathlib import Path
import re
import shlex

ap=argparse.ArgumentParser(); ap.add_argument('--build',type=Path,required=True); ap.add_argument('--workspaces',type=Path,required=True)
a=ap.parse_args(); out=a.build/'dependencies'; out.mkdir(exist_ok=False)
b=a.workspaces/'westlake-harness-bms-deploy'
scripts=[]
for group in ('n2','n4'):
    text=(a.build/f'{group}.sh').read_text()
    text=re.sub(r'^OUT=.*$', 'OUT='+shlex.quote(str(out/group)),text,flags=re.M)
    text=re.sub(r' -c (.+) -o "\$OUT/([^"/]+)\.o"',r' -M -MF "$OUT/\2.d" \1',text)
    text='\n'.join(line for line in text.splitlines() if not line.startswith('sha256sum '))+'\n'
    script=out/f'{group}.sh'; script.write_text(text); scripts.append(script)
commands=json.loads((a.workspaces/'westlake-inputs/generations/u13-runtime-m1-v1/build/u13/extra-commands.json').read_text())
emboss=['#!/usr/bin/env bash','set -euo pipefail']
for argv in commands:
    i=argv.index('-o'); original=Path(argv[i+1]); del argv[i:i+2]
    argv.remove('-c'); argv+=['-M','-MF',str(out/(original.stem+'.d'))]
    emboss.append(shlex.join(argv))
script=out/'emboss.sh'; script.write_text('\n'.join(emboss)+'\n'); scripts.append(script)
f=b/'bms/src/.work/product-tls-generation/frozen'
src=b/'bms/src/.work/b87-native/adapter/framework/android-runtime/src/sqlite/sqlite3.c'
argv=[str(f/'toolchain/bin/clang-15'),'--target=aarch64-linux-ohos','--sysroot='+str(b/'bms/src/.work/b6-latest/oh/out/wukong100/obj/third_party/musl/usr'),'-I'+str(b/'bms/src/.work/b6-latest/oh/out/wukong100/obj/third_party/musl/usr/include/aarch64-linux-ohos'),'-fPIC','-O2']
argv += ['-D'+x for x in ('SQLITE_ENABLE_COLUMN_METADATA','SQLITE_ENABLE_FTS3','SQLITE_ENABLE_FTS3_PARENTHESIS','SQLITE_ENABLE_FTS4','SQLITE_ENABLE_FTS5','SQLITE_ENABLE_RTREE','SQLITE_ENABLE_JSON1','SQLITE_ENABLE_DBSTAT_VTAB','SQLITE_THREADSAFE=2','SQLITE_TEMP_STORE=3')]
argv+=['-M','-MF',str(out/'sqlite3.d'),str(src)]
script=out/'sqlite.sh'; script.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'+shlex.join(argv)+'\n'); scripts.append(script)
runner=['#!/usr/bin/env bash','set -euo pipefail','cd '+shlex.quote(str(b)), 'export LD_LIBRARY_PATH='+shlex.quote(str(b/'bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain/runtime'))]
runner+=['bash '+shlex.quote(str(s)) for s in scripts]
(out/'run.sh').write_text('\n'.join(runner)+'\n'); print(out/'run.sh')
