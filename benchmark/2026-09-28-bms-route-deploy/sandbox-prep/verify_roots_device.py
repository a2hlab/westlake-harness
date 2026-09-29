"""Read root attributes, repeat only Wikipedia preparation, read back again."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'batch'))
import bms_batch as b
out=root/'evidence/roots';out.mkdir(exist_ok=False)
board=b.Board('5ea34a4500000000000000001123012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands')
board.boot=json.loads((root/'evidence/results.json').read_text())['boot_id']
paths=['el1/100/base','el1/100/database','el2/100/base','el2/100/database','el2/100/sharefiles','el3/100/base','el3/100/database','el4/100/base','el4/100/database','el2/100/log']
def read(pkg):
 command='\n'.join('stat -c "'+p+' %a %u %g %C" /data/app/'+p+'/'+pkg for p in paths)
 _,text=board.shell(command);return text
hello=read('com.example.helloworld');before=read('org.wikipedia')
_,text=board.shell('bm dump -n org.wikipedia');uid=b.parse_bundle(text,'org.wikipedia')['uid']
receipt=b.prepare_sandbox(board,'org.wikipedia',uid,out)
after=read('org.wikipedia')
(out/'helloworld.txt').write_text(hello+'\n');(out/'wikipedia-before-repeat.txt').write_text(before+'\n');(out/'wikipedia-after-repeat.txt').write_text(after+'\n')
(out/'result.json').write_text(json.dumps({'serial':board.serial,'boot_id':board.boot,'uid':uid,'repeat_receipt':receipt,'unchanged':before==after},indent=2)+'\n')
print('repeat preparation:',receipt['return_code'],'attributes unchanged:',before==after)
