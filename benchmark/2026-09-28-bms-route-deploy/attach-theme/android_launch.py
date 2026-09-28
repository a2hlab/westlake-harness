from pathlib import Path
import subprocess,json,time,xml.etree.ElementTree as ET,re
r=Path(__file__).resolve().parent/'android-reference'
a='/Users/zhaoyue/Library/Android/sdk/platform-tools/adb';s='N100CU025C18D000128';lock='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh'
def run(args,binary=False):
 assert subprocess.check_output([lock,'held',s],text=True).split()[0]=='cx-t0'
 p=subprocess.run([a,'-s',s,*args],check=True,capture_output=True,timeout=60)
 return p.stdout if binary else p.stdout.decode()
run(['shell','input','swipe','600','1600','600','500','400']);time.sleep(1)
run(['shell','uiautomator','dump','/data/local/tmp/b6-reference-ui.xml'])
xml=run(['shell','cat','/data/local/tmp/b6-reference-ui.xml']);(r/'drawer.xml').write_text(xml)
(r/'drawer.png').write_bytes(run(['exec-out','screencap','-p'],True))
items=[e for e in ET.fromstring(xml).iter('node') if e.attrib.get('text')=='Wikipedia' or e.attrib.get('content-desc')=='Wikipedia']
if not items:print('Wikipedia not visible in drawer; inspect screenshot');raise SystemExit(2)
e=items[0];xy=list(map(int,re.findall(r'\d+',e.attrib['bounds'])));x=(xy[0]+xy[2])//2;y=(xy[1]+xy[3])//2
run(['shell','am','force-stop','org.wikipedia'])
run(['shell','input','tap',str(x),str(y)]);time.sleep(15)
(r/'final.png').write_bytes(run(['exec-out','screencap','-p'],True))
pids=run(['shell','pidof','org.wikipedia']);(r/'pids-after.txt').write_text(pids)
rec=json.loads((r/'record.json').read_text());rec.update(desktop_clicked=True,icon=e.attrib,wait_seconds=15,pids_after=pids.split());(r/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
print('desktop clicked',e.attrib['bounds'],'pids',pids)
