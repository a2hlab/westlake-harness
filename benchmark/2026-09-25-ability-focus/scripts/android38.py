"""Host Android reference: exact serial, original APK, atrace with explicit input tap path."""
import pathlib,subprocess,time,json,sys
S='N100CU025C18D000128';P='com.ss.android.article.news'
R=pathlib.Path(__file__).resolve().parents[1]/'android-reference'/sys.argv[1];R.mkdir(parents=True,exist_ok=True)
def cmd(args,label):
 start=time.time();p=subprocess.run(['adb','-s',S,*args],capture_output=True)
 (R/(label+'.txt')).write_bytes(p.stdout+p.stderr)
 with (R/'operations.jsonl').open('a') as f:f.write(json.dumps({'epoch':start,'argv':args,'rc':p.returncode,'artifact':label+'.txt'})+'\n')
 return p.stdout
if '--fresh' in sys.argv:
 cmd(['shell','am force-stop '+P+'; pm clear '+P+'; input keyevent KEYCODE_WAKEUP; wm dismiss-keyguard; am start -W -n '+P+'/.activity.MainActivity'],'prepare')
 time.sleep(2)
 cmd(['shell','uiautomator dump /data/local/tmp/ability38-consent.xml'],'consent-dump')
 xml=cmd(['shell','cat /data/local/tmp/ability38-consent.xml'],'consent-xml')
 import xml.etree.ElementTree as ET,re
 consent=next(n for n in ET.fromstring(xml).iter('node') if n.get('text')=='同意')
 bounds=list(map(int,re.findall(r'\d+',consent.get('bounds'))));cx=(bounds[0]+bounds[2])//2;cy=(bounds[1]+bounds[3])//2
else:cx,cy=600,1238
# Exact consent coordinates come from the actual UI hierarchy.

cmd(['shell',f'echo CONSENT_BEFORE; cat /proc/uptime; input tap {cx} {cy}; echo CONSENT_AFTER; cat /proc/uptime'],'consent')
t0=time.monotonic()
logfile=(R/'logcat.txt').open('wb');logproc=subprocess.Popen(['adb','-s',S,'logcat','-v','monotonic','-b','all'],stdout=logfile,stderr=subprocess.STDOUT)
try:
 time.sleep(max(0,t0+25-time.monotonic()))
 (R/'before.png').write_bytes(subprocess.check_output(['adb','-s',S,'exec-out','screencap','-p']))
 cmd(['shell','atrace --async_start -b 16384 -a '+P+' input view wm am sched binder_driver'],'atrace-start')
 time.sleep(max(0,t0+30-time.monotonic()))
 cmd(['shell','echo INPUT_BEFORE; cat /proc/uptime; input tap 380 297; echo INPUT_AFTER; cat /proc/uptime'],'physical-reference')
 after=time.monotonic()
 for deadline in (2,5,45):
  time.sleep(max(0,after+deadline-time.monotonic()))
  cmd(['shell','cat /proc/uptime; dumpsys activity activities | grep -E "topResumedActivity|mResumedActivity"'],'after-'+str(deadline)+'s-state')
  (R/('after-'+str(deadline)+'s.png')).write_bytes(subprocess.check_output(['adb','-s',S,'exec-out','screencap','-p']))
  if deadline==5:cmd(['shell','atrace --async_stop'],'atrace')
finally:
 logproc.terminate();logproc.wait(timeout=10);logfile.close()
print('ANDROID_REFERENCE_DONE',R,flush=True)
