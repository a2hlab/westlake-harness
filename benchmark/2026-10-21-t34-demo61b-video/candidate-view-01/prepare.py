#!/usr/bin/env python3
"""Offline generation only; no device transport. Collect immediately after candidate boot."""
import argparse, hashlib, json, re, shlex
from pathlib import Path
SERIAL='61b0657200000000000000000324012c'
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
EXE='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
HOST='bf8ddab28302302242b9c2014aea11717c0d55c62fc526339dce6959f007b32c'
KNOWN={'liboh_adapter_bridge.so':'b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4','lib/arm64-v8a/libmffmpeg.so':'d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4','lib/arm64-v8a/libttmplayer.so':'0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471','webview-t-lib/libwebview_bionic_shim.so':'7f8d75bbf09e28e2b57a4621f1181ff944e79e462b78707c620dd67aef0b0bcb','libopensles_android_compat.so':'6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'}
RUN30='8d996f946e36de839280c7524dbb53d0538f922e3d8886a9895f522cac5f4954'
FILE_READ = r"""file_error() {
 printf 'CV_FILE_ERROR|%s|%s|%s\n' "$1" "$2" "$3"
 OBS_BAD=82
}
file_read() {
 role=$1; rel=$2; path=$3; want=$4
 if test ! -f "$path"; then file_error "$role" "$rel" MISSING_OR_NOT_REGULAR; return 0; fi
 if ! before=$(stat -L -c %d:%i:%s:%a:%u:%g "$path"); then file_error "$role" "$rel" PRESTAT_FAILED; return 0; fi
 printf 'CV_FILE_PRESTAT|%s|%s|%s\n' "$role" "$rel" "$before"
 if ! digest=$(sha256sum "$path"); then file_error "$role" "$rel" HASH_FAILED; return 0; fi
 digest=${digest%% *}
 printf 'CV_FILE_HASH|%s|%s|%s\n' "$role" "$rel" "$digest"
 if ! after=$(stat -L -c %d:%i:%s:%a:%u:%g "$path"); then file_error "$role" "$rel" POSTSTAT_FAILED; return 0; fi
 printf 'CV_FILE|%s|%s|%s|%s\n' "$role" "$rel" "$after" "$digest"
 if test "$before" != "$after"; then file_error "$role" "$rel" STAT_CHANGED; fi
 if test "$digest" != "$want"; then file_error "$role" "$rel" SHA_MISMATCH; fi
 return 0
}
"""

def positive(x):
    assert type(x) is int and 0 < x < 2**31
    return x

def validate(p,run):
    assert p['serial']==SERIAL and p['runtime']==RT
    assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',p['boot'])
    assert p['boot']!=p['before_boot'], 'candidate boot must differ from admission boot'
    positive(p['wid']); assert re.fullmatch(r'mnt:\[[0-9]+\]',p['init_mnt']); ids=[]
    for role in ['parent','host','child']:
        a=p.get(role)
        if a is None:
            assert role=='child';continue
        ids.append(positive(a['pid']));positive(a['birth']);positive(a['ppid'])
        assert a['uid']==(0 if role=='parent' else 20011206)
        assert a['exe_sha256']==(HOST if role=='host' else EXE)
        assert re.fullmatch(r'mnt:\[[0-9]+\]',a['mnt'])
        assert a['mnt']!=p['init_mnt'] if role in ('parent','child') else True
    assert len(ids)==len(set(ids));assert p['parent']['ppid']==1
    if p.get('child'):assert p['child']['ppid']==p['parent']['pid']
    lines=re.findall(rb'^export WL_PARENT_ID=([0-9]+)$',run,re.M)
    assert len(lines)==1 and int(lines[0])==p['wid']
    normalized=re.sub(rb'^export WL_PARENT_ID=[0-9]+$',b'export WL_PARENT_ID=30',run,flags=re.M)
    assert hashlib.sha256(normalized).hexdigest()==RUN30
    expected={'run.sh':hashlib.sha256(run).hexdigest(),**KNOWN}
    assert p['expected_sha256']==expected
    return expected

def process_guard(a):
    pid=a['pid'];q=shlex.quote
    return f'''row=$(cat /proc/{pid}/stat) || exit 81
rest=${{row##*) }}; set -- $rest
test "${{20}}" = {a['birth']} && test "$1" != Z && test "$1" != X && test "$2" = {a['ppid']} || exit 81
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{pid}/status) || exit 81; set -- $u
test "$1:$2:$3:$4" = {':'.join([str(a['uid'])]*4)} || exit 81
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{pid}/status)" = 0 || exit 81
test "$(readlink /proc/{pid}/ns/mnt)" = {q(a['mnt'])} || exit 81
h=$(sha256sum /proc/{pid}/exe) || exit 81; test "${{h%% *}}" = {a['exe_sha256']} || exit 81
printf 'IDENTITY {pid} '; cat /proc/{pid}/stat || exit 81
'''

def prepare(p,run,hdc):
    expected=validate(p,run);q=shlex.quote;pid=p['parent']['pid'];hid=p['host']['pid']
    guard=f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(p["boot"])} || exit 81\n'
    guard+=f'test "$(readlink /proc/1/ns/mnt)" = {q(p["init_mnt"])} || exit 81\n'
    guard+=''.join(process_guard(p[r]) for r in ['parent','host','child'] if p.get(r))
    guard+=f'''envrows=$(strings /proc/{pid}/environ) || exit 81
wids=$(printf '%s\\n' "$envrows" | sed -n 's/^WL_PARENT_ID=//p')
test "$wids" = {p['wid']} || exit 81
hc=$(strings /proc/{hid}/cmdline) || exit 81
test "$hc" = org.westlake.imehost || exit 81
wm=$(hidumper -s WindowManagerService -a '-a') || exit 81
printf '%s\\n' "$wm" | grep -E '^imehost0[[:space:]]+[0-9]+[[:space:]]+{hid}[[:space:]]+{p['wid']}[[:space:]]' >/dev/null || exit 81
'''
    shell='set -eu\n'+guard+"OBS_BAD=0\necho CANDIDATE_VIEW_BEGIN\n"
    shell+=FILE_READ
    for role,root in [('physical',RT),('parent',f'/proc/{pid}/root/data/local/tmp/asx')]+([('child',f'/proc/{p["child"]["pid"]}/root/data/local/tmp/asx')] if p.get('child') else []):
        for rel,digest in expected.items():shell+=f'file_read {role} {q(rel)} {q(root+"/"+rel)} {digest}\n'
        shell+=f'''rw=$(sed -n 's/^export WL_PARENT_ID=//p' {q(root+'/run.sh')}) || {{ rw=UNKNOWN_READ_FAILED; OBS_BAD=82; }}
printf 'CV_RUN_WID|{role}|%s\\n' "$rw"
test "$rw" = {p['wid']} || OBS_BAD=82
'''
    for role in ['parent','child']:
        if not p.get(role):shell+='echo CHILD_UNKNOWN_NOT_SELECTED\n';continue
        n=p[role]['pid'];shell+=f'echo MAPS_BEGIN_{role}; cat /proc/{n}/maps || {{ echo UNKNOWN_MAPS_{role}; OBS_BAD=82; }}; echo MAPS_END_{role}\necho MOUNTS_BEGIN_{role}; cat /proc/{n}/mountinfo || {{ echo UNKNOWN_MOUNTS_{role}; OBS_BAD=82; }}; echo MOUNTS_END_{role}\n'
    shell+=guard+"printf 'CV_REMOTE_RC|%s\\n' \"$OBS_BAD\"\necho CANDIDATE_VIEW_END_IDENTITY_MATCH\nexit \"$OBS_BAD\"\n"
    assert len(shell.encode())<32768
    return [str(hdc),'-t',SERIAL,'shell',shell]

def main():
    a=argparse.ArgumentParser();a.add_argument('--profile',type=Path,required=True);a.add_argument('--candidate-run',type=Path,required=True);a.add_argument('--hdc',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    p=json.loads(a.profile.read_text());assert not p.get('fixture_only'), 'offline fixture is not an execution profile';argv=prepare(p,a.candidate_run.read_bytes(),a.hdc);a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'collect.argv.json').write_text(json.dumps(argv,indent=2)+'\n');(a.out/'collect.sh').write_text(argv[-1]);(a.out/'profile.json').write_text(json.dumps(p,indent=2)+'\n')
    print('PREPARED_ONLY_NO_DEVICE_CALL')
if __name__=='__main__':main()
