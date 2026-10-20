import json, pathlib, subprocess, hashlib, datetime,time
base=pathlib.Path(__file__).parent; repo=pathlib.Path.cwd();d=base/'t14-5cd-window-01';d.mkdir(exist_ok=False)
hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc';serial='5cd1e3dd00000000000000000923012c';boot='0525bb05-f714-42ad-90f0-ecdb10356c4f';run='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'
def call(tag,args,timeout=20):
 (d/(tag+'.argv.json')).write_text(json.dumps(args));r=subprocess.run(args,capture_output=True,timeout=timeout);(d/(tag+'.stdout')).write_bytes(r.stdout);(d/(tag+'.stderr')).write_bytes(r.stderr);(d/(tag+'.rc')).write_text(str(r.returncode));assert r.returncode==0,(tag,r.stderr);return r.stdout.decode()
call('lock',['bash',str(repo/'scripts/lab/board_note.sh'),'lock',str(repo/'.octos/boards/app-lighting.md'),serial,'outer(codex)','T14 existing-child single normal play, no deploy, 600s including restore'])
holder=call('holder',['bash',str(repo/'scripts/lab/board_note.sh'),'held',serial]).strip();start=datetime.datetime.fromisoformat(holder.split()[2]).timestamp();(d/'context.json').write_text(json.dumps(dict(repo=str(repo),hdc=hdc,holder=holder,start=start,serial=serial)))
s='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+'; echo BOOT; cat /proc/sys/kernel/random/boot_id; echo INIT_MNT; readlink /proc/1/ns/mnt; echo RUN; sha256sum '+run+'; '
for role,pid,birth in [('parent',19163,7265322),('child',1601,7706984),('host',18952,7265069)]:
 s+=f'echo ROLE_{role}; cat /proc/{pid}/stat; sed -n "/^Uid:/p;/^TracerPid:/p" /proc/{pid}/status; readlink /proc/{pid}/ns/mnt; sha256sum /proc/{pid}/exe; r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {birth}; test "$1" != Z; test "$1" != X; '
s+='test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+'; echo T14_PROFILE_COMPLETE'
raw=call('readonly',[hdc,'-t',serial,'shell',s]);assert raw.rstrip().endswith('T14_PROFILE_COMPLETE');print(raw)
p=json.loads((repo/'benchmark/2026-10-20-t14-play-observation/profile.template.json').read_text());p.update(boot=boot,observed_at=time.time(),readonly_receipt_sha256=hashlib.sha256((d/'readonly.stdout').read_bytes()).hexdigest(),init_mnt=raw.split('INIT_MNT\n')[1].splitlines()[0].strip(),run_sha256=raw.split('RUN\n')[1].split()[0])
for role in ('parent','child','host'):
 lines=raw.split('ROLE_'+role+'\n')[1].splitlines();st=lines[0];tail=st.rsplit(') ',1)[1].split();uids=next(x for x in lines if x.startswith('Uid:')).split()[1:];assert len(set(uids))==1;assert next(x for x in lines if x.startswith('TracerPid:')).split()[1]=='0';p[role]=dict(pid=int(st.split()[0]),ppid=int(tail[1]),birth=int(tail[19]),uid=int(uids[0]),mnt=next(x for x in lines if x.startswith('mnt:[')).strip(),exe_sha256=next(x for x in lines if '/proc/'+st.split()[0]+'/exe' in x).split()[0])
(d/'profile.json').write_text(json.dumps(p,indent=2));print(json.dumps(p,indent=2))
