from pathlib import Path
import json,subprocess,hashlib,time,sys
repo=Path.cwd();base=Path(__file__).parent/'t16-5cd-window-01';c=json.loads((base/'context.json').read_text());out=base/'candidate-profile';out.mkdir(exist_ok=False);boot=json.loads((base/'candidate-boot.json').read_text())['boot'];run='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'
s='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+'; echo INIT_MNT; readlink /proc/1/ns/mnt; echo RUN; sha256sum '+run+'; '
for role,pid in [('parent',6395),('child',8151),('host',6170)]:
 s+=f'echo ROLE_{role}; cat /proc/{pid}/stat; sed -n "/^Uid:/p;/^TracerPid:/p" /proc/{pid}/status; readlink /proc/{pid}/ns/mnt; sha256sum /proc/{pid}/exe; '
s+='echo CANDIDATES; '
for rel in ['run.sh','libopensles_android_compat.so','lib/arm64-v8a/libmffmpeg.so','lib/arm64-v8a/libttmplayer.so']:
 for prefix in [run.rsplit('/',1)[0],'/proc/6395/root/data/local/tmp/asx']:
  s+='sha256sum '+prefix+'/'+rel+'; stat -L -c "%d:%i:%a:%u:%g" '+prefix+'/'+rel+'; '
s+='echo MAPS; cat /proc/8151/maps; test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+'; echo T16_PROFILE_COMPLETE';a=[c['hdc'],'-t',c['serial'],'shell',s];(out/'argv.json').write_text(json.dumps(a));r=subprocess.run(a,capture_output=True,timeout=20);(out/'stdout').write_bytes(r.stdout);(out/'stderr').write_bytes(r.stderr);(out/'rc').write_text(str(r.returncode));raw=r.stdout.decode();assert r.returncode==0 and raw.rstrip().endswith('T16_PROFILE_COMPLETE')
p=json.loads((repo/'benchmark/2026-10-20-t14-play-observation/profile.template.json').read_text());p.update(boot=boot,observed_at=time.time(),readonly_receipt_sha256=hashlib.sha256(r.stdout).hexdigest(),init_mnt=raw.split('INIT_MNT\n')[1].splitlines()[0].strip(),run_sha256=raw.split('RUN\n')[1].split()[0])
for role in ('parent','child','host'):
 lines=raw.split('ROLE_'+role+'\n')[1].splitlines();st=lines[0];tail=st.rsplit(') ',1)[1].split();uids=next(x for x in lines if x.startswith('Uid:')).split()[1:];assert len(set(uids))==1;assert next(x for x in lines if x.startswith('TracerPid:')).split()[1]=='0';p[role]=dict(pid=int(st.split()[0]),ppid=int(tail[1]),birth=int(tail[19]),uid=int(uids[0]),mnt=next(x for x in lines if x.startswith('mnt:[')).strip(),exe_sha256=next(x for x in lines if '/proc/'+st.split()[0]+'/exe' in x).split()[0])
sys.path.insert(0,str(repo/'benchmark/2026-10-20-t14-play-observation'));import observe;observe.profile(p);(out/'profile.json').write_text(json.dumps(p,indent=2));print(json.dumps(p,indent=2))
