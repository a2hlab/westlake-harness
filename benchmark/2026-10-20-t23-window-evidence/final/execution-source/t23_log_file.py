from pathlib import Path
import subprocess,json,time,hashlib
repo=Path.cwd();base=Path(__file__).parent;w=base/'t23-5cd-window-01';c=json.loads((w/'context.json').read_text());o=w/'candidate-prefix-file';o.mkdir(exist_ok=False);boot='af001b38-659a-4f1f-9dd7-b85960587a2c';remote='/data/local/tmp/t23-log-prefix-1792467138';src='/data/service/el1/public/appspawnx/adapter_child_7655.stderr';end=33156759

def call(tag,argv):
 assert time.time()-c['start']<1200
 h=subprocess.run(['bash',str(repo/'scripts/lab/board_note.sh'),'held',c['serial']],capture_output=True,timeout=3);assert h.returncode==0 and h.stdout.decode().strip()==c['holder']
 (o/(tag+'.argv.json')).write_text(json.dumps(argv))
 with (o/(tag+'.stdout')).open('wb') as so,(o/(tag+'.stderr')).open('wb') as se:r=subprocess.run(argv,stdout=so,stderr=se,timeout=30)
 (o/(tag+'.rc')).write_text(str(r.returncode));assert r.returncode==0
 return (o/(tag+'.stdout')).read_text()
g='test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+'; test "$(stat -c %d:%i '+src+')" = 66352:191839; test "$(stat -c %s '+src+')" -ge '+str(end)
cmd='(set -eu; '+g+'; test ! -e '+remote+'; dd if='+src+' of='+remote+' bs=4096 count=8095; test "$(stat -c %s '+remote+')" = 33157120; '+g+'; sha256sum '+remote+'; echo PREFIX_COPY_COMPLETE)'
s=call('copy',[c['hdc'],'-t',c['serial'],'shell',cmd]);assert 'PREFIX_COPY_COMPLETE' in s
call('receive',[c['hdc'],'-t',c['serial'],'file','recv',remote,str(o/'received.raw')]);b=(o/'received.raw').read_bytes();sha=hashlib.sha256(b).hexdigest();assert len(b)==33157120 and sha in s
s=call('after',[c['hdc'],'-t',c['serial'],'shell','(set -eu; '+g+'; cat /proc/7655/stat; echo PREFIX_AFTER_COMPLETE)']);assert 'PREFIX_AFTER_COMPLETE' in s
b=b[:end];(o/'selected.raw').write_bytes(b);result=dict(status='FIXED_PREFIX_COMPLETE',boot=boot,pid=7655,source_start=0,source_end=end,selected_bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),immutability_not_proven=True);(o/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
