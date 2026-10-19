#!/bin/bash
# R10 isolated budget successor. --plan is read-only; --run must be explicitly requested.
# No player derivation, source edit, device command or deployment is performed.
set -euo pipefail
case "${1:---plan}" in
  --plan)
    cat <<'PLAN'
{
  "status": "RECIPE_REVIEW_ONLY_NOT_BUILT_NOT_ADMITTED",
  "required_environment": ["SOURCE_REPO", "OH_NATIVE", "LIBLOG_INPUT", "OUT"],
  "inputs": {
    "compat_c": "cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351",
    "mirror_c": "419aa6ea6c41792c3d886ab312855c3c677dbe92430dadfe2c253fd851de990e",
    "original_compat": "9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f",
    "link_input_real_liblog": "d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4"
  },
  "sequence": ["fresh OUT and raw logs", "check_frozen --git SOURCE_REPO", "copy and verify exact inputs", "pin Docker image and OH tools/sysroot", "build historical link-only OpenSL anchor", "link both unchanged C files with explicit real liblog SONAME dependency and -z defs", "strip", "compare original/new exports and dependencies; record vprint GOT", "hash artifacts and all raw receipts"],
  "scope": "Only compat build. liblog is link input, never a deployment payload. Run/media and player are not produced here.",
  "pending": ["Production execution rc/logs and output SHA", "Runtime namespace resolves explicit liblog dependency to exact d8ad instance", "Player import binds unique new compat export", "Reuse existing exact player0b4d/media d288/run b562; no derivation performed"]
}
PLAN
    exit 0 ;;
  --run) [ "$#" -eq 1 ] || exit 2 ;;
  *) echo 'usage: build_candidate.sh [--plan|--run]' >&2; exit 2 ;;
esac
: "${SOURCE_REPO:?set the reviewed source repository root}"
: "${OH_NATIVE:?set the existing container-visible OH SDK native root}"
: "${LIBLOG_INPUT:?set the exact received d8ad liblog.so input}"
: "${OUT:?set a fresh persistent output directory, not /tmp}"
case "$OUT" in /*) ;; *) echo 'OUT must be absolute' >&2; exit 2;; esac
case "$OUT" in /tmp/*|/private/tmp/*) echo 'OUT must be persistent' >&2; exit 2;; esac
SOURCE_REPO=$(cd "$SOURCE_REPO" && pwd)
DB=${R10_DOCKBUILD:-"$SOURCE_REPO/scripts/lab/dockbuild.sh"}
case "$DB" in /*) ;; *) echo 'R10_DOCKBUILD must be an absolute reviewed script path' >&2; exit 2;; esac
test -f "$DB"
B="$SOURCE_REPO/benchmark/2026-10-19-toutiao-video-playback"
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
mkdir "$OUT" # Existing output, including a symlink, is refused.
mkdir "$OUT/raw" "$OUT/src" "$OUT/inputs" "$OUT/link-only.NOT-FOR-DEPLOY" "$OUT/unstripped" "$OUT/artifacts"
cd "$OUT"
step() {
  local name=$1 rc; shift
  printf '%q ' "$@" > "raw/$name.command"; printf '\n' >> "raw/$name.command"
  if "$@" > "raw/$name.stdout" 2> "raw/$name.stderr"; then rc=0; else rc=$?; fi
  printf '%s\n' "$rc" > "raw/$name.rc"
  printf '%s rc=%s\n' "$name" "$rc"
  [ "$rc" -eq 0 ] || exit "$rc"
}
step 00-frozen python3 "$SOURCE_REPO/scripts/lab/check_frozen.py" --git "$SOURCE_REPO" \
  --registry "$SOURCE_REPO/knowledge/frozen/frozen.json"
cp "$B/candidate/src/opensles_android_compat.c" src/
cp "$(dirname "$SELF")/ttplayer_log_mirror.c" src/
cp "$B/static/selected-change/link_only_stub.c" src/
cp "$B/candidate/deploy-inputs/libopensles_android_compat.so" inputs/original-compat.so
cp "$LIBLOG_INPUT" inputs/liblog.so
cp "$B/candidate/toolchain-manifest.json" inputs/original-toolchain-manifest.json
cp "$SELF" recipe.sh
cat > inputs.sha256 <<'PINS'
cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351  src/opensles_android_compat.c
419aa6ea6c41792c3d886ab312855c3c677dbe92430dadfe2c253fd851de990e  src/ttplayer_log_mirror.c
fa47585b8fb702e8da05c52d732c9c964b5ec50a34edfa6815dea7f962898e13  src/link_only_stub.c
9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f  inputs/original-compat.so
d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4  inputs/liblog.so
ec28a440500411b265789399b609b728e0f4ef29ba386a570edac3d9556e5138  inputs/original-toolchain-manifest.json
PINS
step 01-inputs shasum -a 256 -c inputs.sha256
step 01a-reused python3 "$(dirname "$SELF")/verify.py" source --inputs-root "$SOURCE_REPO"
step 02-recipe-tools shasum -a 256 recipe.sh "$DB" "$SOURCE_REPO/scripts/lab/check_frozen.py"
IMG=${DOCKBUILD_IMAGE:-a2hlab-build:24.04}
step 03-image docker image inspect "$IMG" --format '{{.Id}}'
[ "$(cat raw/03-image.stdout)" = 'sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63' ] || {
  echo 'Docker image drift' >&2; exit 2;
}
# Do not use dockbuild cc's embedded author path: the explicit OH_NATIVE drives
# every compiler/readelf/strip command below. dockbuild supplies only the mounts.
cat > container-stage.sh <<'CONTAINER'
#!/bin/bash
set -euo pipefail
OH=$1; action=$2
CC="$OH/llvm/bin/clang-15"; RE="$OH/llvm/bin/llvm-readelf"
case "$action" in
  tools)
    printf '%s  %s\n' \
      b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913 "$CC" \
      8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4 "$OH/llvm/bin/lld" \
      21aedd438c723f6aca5fad6a490393dcebce8d0141e78ab34dc7234566653516 "$OH/llvm/bin/llvm-strip" \
      bc65ae472048d0f9c8b7698d70f3f97c60210da2f3eab0f581f2f7ecd868dea8 "$RE" \
      86d5e1cd6437f1fd4df9df7e5aa32c237bd3c441726612c48e4e44b712623eb1 "$OH/sysroot/usr/lib/aarch64-linux-ohos/libc.so" | sha256sum -c -
    LIBDL=$("$CC" --target=aarch64-linux-ohos --sysroot="$OH/sysroot" -print-file-name=libdl.a)
    test -f "$LIBDL"
    sha256sum "$LIBDL"
    "$CC" --version ;;
  anchor)
    "$CC" --target=aarch64-linux-ohos --sysroot="$OH/sysroot" -fPIC -O2 -shared -fuse-ld=lld \
      -Wl,-z,relro,-z,now src/link_only_stub.c -Wl,-soname,libOpenSLES.so \
      -o link-only.NOT-FOR-DEPLOY/libOpenSLES.so ;;
  link)
    "$CC" --target=aarch64-linux-ohos --sysroot="$OH/sysroot" -fPIC -O2 -g \
      -Wall -Wextra -Werror -shared -fuse-ld=lld -Wl,-z,relro,-z,now,-z,defs --unwindlib=none -Wl,--why-extract=raw/20-archive-extraction.txt \
      -Wl,-soname,libopensles_android_compat.so src/opensles_android_compat.c src/ttplayer_log_mirror.c \
      -ldl -Llink-only.NOT-FOR-DEPLOY -Linputs -Wl,--no-as-needed -lOpenSLES -l:liblog.so \
      -Wl,--as-needed -o unstripped/libopensles_android_compat.so ;;
  strip)
    cp unstripped/libopensles_android_compat.so artifacts/libopensles_android_compat.so
    "$OH/llvm/bin/llvm-strip" --strip-unneeded artifacts/libopensles_android_compat.so ;;
  old-abi) "$RE" -h -dW --dyn-syms inputs/original-compat.so ;;
  new-abi) "$RE" -h -dW --dyn-syms artifacts/libopensles_android_compat.so ;;
  liblog-abi) "$RE" -h -dW --dyn-syms inputs/liblog.so ;;
  relocations) "$RE" -rW artifacts/libopensles_android_compat.so ;;
  *) exit 2 ;;
esac
CONTAINER
container_step() {
  local label=$1 action=$2 command
  printf -v command 'bash %q %q %q' "$OUT/container-stage.sh" "$OH_NATIVE" "$action"
  step "$label" bash "$DB" run -- "$command"
}
container_step 04-tools tools
container_step 05-liblog-abi liblog-abi
container_step 10-anchor anchor
container_step 20-link link
container_step 21-strip strip
container_step 30-old-abi old-abi
container_step 31-new-abi new-abi
container_step 32-relocations relocations
cat > compare-abi.py <<'PY'
from pathlib import Path
import json,re

def read(name):
    text=Path('raw/'+name+'.stdout').read_text()
    assert 'AArch64' in text and 'ELF64' in text
    needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',text)
    symbols={}
    for line in text.splitlines():
        fields=line.split()
        if len(fields)==8 and fields[0].rstrip(':').isdigit():
            symbols[fields[7]]={'size':int(fields[2]),'type':fields[3],
                'bind':fields[4],'vis':fields[5],'ndx':fields[6]}
    return text,needed,symbols

ot,on,os=read('30-old-abi'); nt,nn,ns=read('31-new-abi'); lt,ln,ls=read('05-liblog-abi')
exports=lambda sy:{n:s for n,s in sy.items() if s['ndx']!='UND' and s['bind'] in ('GLOBAL','WEAK')}
oe,ne=exports(os),exports(ns)
new='__wl_ttlog_00000659'
assert set(ne)==set(oe)|{new}, (set(oe),set(ne))
for name in oe:
    for key in ('type','bind','vis'): assert oe[name][key]==ne[name][key], (name,key)
    if oe[name]['type']=='OBJECT': assert oe[name]['size']==ne[name]['size'], name
assert ne[new]['type']=='FUNC' and ne[new]['bind']=='GLOBAL' and ne[new]['vis']=='DEFAULT'
assert sorted(nn)==sorted(on+['liblog.so']), (on,nn)
assert '(SONAME)' in lt and '[liblog.so]' in lt
assert ns['__android_log_vprint']['ndx']=='UND' and ns['__android_log_vprint']['bind']=='GLOBAL'
assert ls['__android_log_vprint']['ndx']!='UND' and ls['__android_log_vprint']['type']=='FUNC'
assert '__android_log_print' not in ns
relocs=Path('raw/32-relocations.stdout').read_text().splitlines()
vprint=[line for line in relocs if '__android_log_vprint' in line]
assert len(vprint)==1 and 'R_AARCH64_JUMP_SLOT' in vprint[0], vprint
report={'scope':'STATIC_ABI_ONLY_NOT_PROVIDER_BINDING','old_needed':on,'new_needed':nn,
        'exports_added':[new],'old_exports_preserved':sorted(oe),'vprint_relocation':vprint,
        'undefined_added':sorted(n for n,s in ns.items() if s['ndx']=='UND' and n not in os),
        'liblog_transitive_needed':ln,'runtime_provider':'UNKNOWN_REQUIRES_EXACT_GOT_READ',
        'original_opensl_source_exact':True}
Path('abi-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
PY
step 33-abi-compare python3 compare-abi.py
step 34-inputs-after shasum -a 256 -c inputs.sha256
step 40-output-sha shasum -a 256 unstripped/libopensles_android_compat.so artifacts/libopensles_android_compat.so
python3 - <<'PY'
from pathlib import Path
import hashlib,json
files=sorted(p for p in Path('.').rglob('*') if p.is_file())
rows=[{'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
Path('build-receipt.json').write_text(json.dumps({'status':'BUILT_OFFLINE_NOT_ADMITTED',
    'files':rows,'public_copy':'Raw logs may contain private local paths. Keep originals; publish separately labelled sanitized copies.',
    'deployable_candidate':'artifacts/libopensles_android_compat.so',
    'never_deploy':['inputs/liblog.so','link-only.NOT-FOR-DEPLOY/libOpenSLES.so'],
    'pending':['actual provider binding','reused player/media/run identities','outer admission']},indent=2)+'\n')
PY
printf 'Offline build complete; not deployment admission. Receipt: %s/build-receipt.json\n' "$OUT"
