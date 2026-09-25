"""Host-only Android consent profile, not a queueMs sample."""
import pathlib,subprocess,time,json,xml.etree.ElementTree as ET,re
A='/Users/zhaoyue/Library/Android/sdk/platform-tools/adb';S='N100CU025C18D000128';P='com.ss.android.article.news'
r=pathlib.Path(__file__).resolve().parents[1]/'android-reference/cpu-1';r.mkdir(parents=True,exist_ok=True)
def cmd(args,label,timeout=120):
 p=subprocess.run([A,'-s',S,*args],capture_output=True,timeout=timeout)
 (r/(label+'.txt')).write_bytes(p.stdout+p.stderr)
 with (r/'operations.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'argv':args,'rc':p.returncode,'artifact':label+'.txt'})+'\n')
 return p.stdout.decode(errors='replace')
cmd(['root'],'adb-root');cmd(['wait-for-device'],'wait-device');cmd(['shell','id'],'identity')
try:
 cmd(['shell','am force-stop '+P+'; pm clear '+P+'; input keyevent KEYCODE_WAKEUP; wm dismiss-keyguard; am start -W -n '+P+'/.activity.MainActivity'],'prepare')
 time.sleep(2);cmd(['shell','uiautomator dump /data/local/tmp/ability38-cpu-consent.xml'],'consent-dump')
 xml=cmd(['shell','cat /data/local/tmp/ability38-cpu-consent.xml'],'consent-xml')
 n=next(n for n in ET.fromstring(xml).iter('node') if n.get('text')=='同意');x,y,x2,y2=map(int,re.findall(r'\d+',n.get('bounds')))
 pid=int(cmd(['shell','pidof '+P],'pid').split()[0])
 (r/'consent-before.png').write_bytes(subprocess.check_output([A,'-s',S,'exec-out','screencap','-p']))
 cmd(['shell',f'cat /proc/uptime; cat /proc/{pid}/task/{pid}/stat; getconf CLK_TCK'],'main-stat-before')
 cmd(['shell',f'cat /proc/{pid}/maps'],'maps-before');cmd(['shell',f'cat /proc/{pid}/task/*/stat'],'tasks-before')
 cmd(['shell',f'echo CONSENT_BEFORE; cat /proc/uptime; input tap {(x+x2)//2} {(y+y2)//2}; echo PROFILE_BEFORE; cat /proc/uptime; simpleperf record -p {pid} -g -f 400 -e task-clock --duration 10 -o /data/local/tmp/ability38-android-cpu.data; echo PROFILE_RC=$?; echo PROFILE_AFTER; cat /proc/uptime'],'record')
 cmd(['shell',f'cat /proc/{pid}/task/*/stat'],'tasks-after')
 cmd(['shell',f'cat /proc/uptime; cat /proc/{pid}/task/{pid}/stat'],'main-stat-after')
 cmd(['pull','/data/local/tmp/ability38-android-cpu.data',str(r/'perf.data')],'pull')
 cmd(['shell',f'simpleperf report -i /data/local/tmp/ability38-android-cpu.data --tids {pid} --sort tid,comm,dso,symbol -n --print-event-count --percent-limit 0'],'report-main')
 cmd(['shell',f'simpleperf report -i /data/local/tmp/ability38-android-cpu.data --tids {pid} --sort tid,comm,dso,symbol -g --percent-limit 0.1'],'report-main-stacks')
 (r/'after-profile.png').write_bytes(subprocess.check_output([A,'-s',S,'exec-out','screencap','-p']))
finally:
 cmd(['shell','am force-stop '+P],'stop')
 cmd(['unroot'],'adb-unroot')
print('ANDROID_CPU_DONE',r)
