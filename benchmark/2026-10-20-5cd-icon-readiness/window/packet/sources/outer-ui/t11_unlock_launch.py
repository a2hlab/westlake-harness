"""Observed lock-screen recovery before the first actual app-icon click; no retries."""
from pathlib import Path
import json,sys,shlex,time
base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';root=base/'t11-5cd-window-01';c=json.loads((root/'context.private.json').read_text());old=json.loads((root/'icon/record.json').read_text());assert not old.get('clicked') and not old.get('selected_icon')
assert 0<=time.time()-c['start']<600
# Reuse the exact reviewed UI class after its capture-only entry, preserving its lock/boot/deadline checks.
sys.argv=['t11_ui.py','capture','--repo',c['repo'],'--root',str(root),'--tag','unlock-before','--holder',c['holder'],'--start',str(c['start']),'--hdc',c['hdc'],'--execute']
import runpy
ns=runpy.run_path(str(base/'t11_ui.py'));UI=ns['UI'];b=ns['b']
out=root/'actual-icon';out.mkdir(exist_ok=False)
board=UI(c['serial'],c['hdc'],'bash '+shlex.quote(str(Path(c['repo'])/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=c['boot'];board.ready()
rc,ps=board.shell('ps -A -o PID,PPID,UID,NAME');assert not any('com.ss.android.article.news' in r for r in ps.splitlines())
remote='/data/local/tmp/t11-5cd-'+str(int(c['start']))+'-actual-icon';board.shell('mkdir -p '+remote)
record={'serial':c['serial'],'boot_id':c['boot'],'key':'toutiao','package':'org.westlake.imehost','screenshots':[],'earlier_actual_icon_clicks':0,'reason':'prior launcher focus guard stopped before any icon selection; actual screenshot shows lock screen'}
try:
 board.shell('power-shell wakeup');board.shell('uitest uiInput swipe 600 1650 600 400');time.sleep(1)
 b.desktop_launch(board,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
 board.shell('power-shell wakeup');shot=b.capture(board,remote+'/screen.jpeg',out/'screen.jpeg');shot['captured']=True;record['screenshots'].append(shot)
 for name,cmd in [('ps','ps -A -o PID,PPID,UID,NAME'),('windows',"hidumper -s WindowManagerService -a '-a'")]:
  rc,text=board.shell(cmd);(out/(name+'.txt')).write_text(text+'\n')
finally:b.save(out/'record.json',record)
print(json.dumps({'out':str(out),'clicked':record.get('clicked',False),'screenshots':record['screenshots']}))
