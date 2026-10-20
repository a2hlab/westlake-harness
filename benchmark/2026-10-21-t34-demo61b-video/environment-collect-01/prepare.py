#!/usr/bin/env python3
"""Offline argv generator only. Does not import or invoke a device transport."""
import argparse,json,re,shlex
from pathlib import Path
SERIALS={'5cd':'5cd1e3dd00000000000000000923012c','61b':'61b0657200000000000000000324012c'}
BCP=('core-oj','core-libart','core-icu4j','conscrypt','okhttp','bouncycastle','apache-xml','framework','adapter-runtime-bcp')
EXE='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
def prepare(profile,hdc):
    serial=profile['serial'];assert serial in SERIALS.values()
    boot=profile['boot'];assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot)
    pid=str(profile['parent_pid']);birth=str(profile['parent_birth']);assert re.fullmatch('[1-9][0-9]*',pid) and re.fullmatch('[1-9][0-9]*',birth)
    ns=profile['parent_mnt'];assert re.fullmatch(r'mnt:\[[0-9]+\]',ns)
    root='/proc/'+pid+'/root';q=shlex.quote
    guard=f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)} || exit 81
row=$(cat /proc/{pid}/stat) || exit 81
rest=${{row##*) }}; set -- $rest
test "${{20}}" = {q(birth)} && test "$1" != Z && test "$1" != X && test "$2" = 1 || exit 81
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{pid}/status); set -- $u
test "$1:$2:$3:$4" = 0:0:0:0 || exit 81
test "$(readlink /proc/{pid}/ns/mnt)" = {q(ns)} || exit 81
test "$(sha256sum /proc/{pid}/exe | cut -d' ' -f1)" = {EXE} || exit 81
'''
    shell='''set -u
# No writes, signals, mounts, UI or app launch. Output stays on stdout.
for tool in cat sed cut strings stat sha256sum sort readlink; do command -v "$tool" >/dev/null 2>&1 || { echo UNKNOWN_REQUIRED_TOOL; exit 82; }; done
'''+guard+f'''printf 'ENV_BEGIN boot=%s parent=%s birth=%s mnt=%s\\n' {q(boot)} {pid} {birth} {q(ns)}
cat /proc/{pid}/stat
printf 'CMDLINE_BEGIN\\n'; strings /proc/{pid}/cmdline || echo UNKNOWN_CMDLINE
printf 'SELECTED_ENV_BEGIN\\n'
strings /proc/{pid}/environ | sed -n '/^BOOTCLASSPATH=/p;/^DEX2OATBOOTCLASSPATH=/p;/^LD_LIBRARY_PATH=/p;/^LD_PRELOAD=/p;/^WESTLAKE_/p;/^ASX_/p;/^WL_PARENT_ID=/p' || echo UNKNOWN_ENV
file_read() {{
 p=$1; kind=$2
 printf 'FILE_BEGIN %s %s\\n' "$kind" "$p"
 if test ! -f "$p"; then echo UNKNOWN_NOT_REGULAR_OR_MISSING; return; fi
 before=$(stat -L -c %d:%i:%s "$p") || {{ echo UNKNOWN_STAT; return; }}
 digest=$(sha256sum "$p") || {{ echo UNKNOWN_HASH; return; }}
 after=$(stat -L -c %d:%i:%s "$p") || {{ echo UNKNOWN_POSTSTAT; return; }}
 if test "$before" != "$after"; then echo UNKNOWN_FILE_CHANGED; return; fi
 printf 'IDENTITY_SIZE %s\\nSHA256 %s\\n' "$after" "$digest"
}}
'''
    for name in BCP:shell+=f'file_read {q(root+"/data/local/tmp/asx/fw/"+name+".jar")} BCP\n'
    shell+=f'''for p in {q(root+'/data/local/tmp/asx/boot/')}*.art {q(root+'/data/local/tmp/asx/boot/')}*.oat {q(root+'/data/local/tmp/asx/boot/')}*.vdex; do file_read "$p" BOOT_IMAGE; done
printf 'MAPS_BEFORE_BEGIN\\n'; cat /proc/{pid}/maps || exit 82
# Only mapped private-asx or system64 shared objects; no recursive filesystem search.
sed -n 's|^[^/]*\\(/.*\\)$|\\1|p' /proc/{pid}/maps | sort -u | while IFS= read -r mapped; do
 case "$mapped" in
 /data/local/tmp/asx/*.so|/system/lib64/*.so) file_read "{root}$mapped" MAPPED_SHARED ;;
 *' (deleted)') printf 'UNKNOWN_DELETED_MAP %s\\n' "$mapped" ;;
 esac
done
printf 'MAPS_AFTER_BEGIN\\n'; cat /proc/{pid}/maps || exit 82
'''+guard+f'''cat /proc/{pid}/stat
printf 'ENV_END_IDENTITY_MATCH boot=%s parent=%s birth=%s mnt=%s\\n' {q(boot)} {pid} {birth} {q(ns)}
'''
    return [str(hdc),'-t',serial,'shell',shell]
def main():
    p=argparse.ArgumentParser();p.add_argument('--profile-5cd',type=Path,required=True);p.add_argument('--profile-61b',type=Path,required=True);p.add_argument('--hdc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    for role,path in [('5cd',a.profile_5cd),('61b',a.profile_61b)]:
        profile=json.loads(path.read_text());assert profile['serial']==SERIALS[role]
        argv=prepare(profile,a.hdc);(a.out/(role+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n');(a.out/(role+'.sh')).write_text(argv[-1])
    print('PREPARED_ONLY: 2 argv; no device invocation')
if __name__=='__main__':main()
