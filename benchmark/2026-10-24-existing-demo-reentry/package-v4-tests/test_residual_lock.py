"""One full-entry offline replay: stale lock tree, visual host-white approval."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
(HERE/'.fixtures').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=HERE/'.fixtures') as folder:
    home=Path(folder)/'home'
    completed=subprocess.run([sys.executable,str(HERE/'fixture_entry.py'),str(home),'residual_lock'],capture_output=True,text=True,timeout=20)
    assert completed.returncode==0,completed.stderr+completed.stdout
    facts=json.loads((home/'fixture-result.json').read_text());run=Path(facts['run']);labels=[x['label'] for x in facts['calls']]
    flags=json.loads((run/'unlocked-layout-flags.json').read_text());assert flags['lock_ids']==['ScreenLockRootComponent'] and flags['credential_like_ids']==[]
    assert (run/'unlocked.jpeg').is_file()
    settle=json.loads((run/'unlock-settle.json').read_text());assert 1.4999<=settle['end_monotonic']-settle['start_monotonic']<=1.5001
    consumed=json.loads((run/'review-consumed.json').read_text());assert consumed['review']['verdict']=='host_white' and consumed['review']['image']=='unlocked.jpeg'
    assert consumed['review']['image_sha256']==hashlib.sha256((run/'unlocked.jpeg').read_bytes()).hexdigest()
    assert labels.count('unlock-once')==labels.count('home')==labels.count('click-once')==1
    assert next(x['at'] for x in facts['calls'] if x['label']=='home')>=consumed['observed_monotonic']
    assert labels.count('cleanup-restore')==labels.count('cleanup-unlock')==1
    assert len({x['pid'] for x in facts['calls']})==1 and facts['device_calls']==0
    result={'status':'PASS','case':'residual lock id + matching outer host_white review through actual start/P0/owner','device_calls':0,'same_owner_pid':facts['pid'],'settle_seconds':settle['end_monotonic']-settle['start_monotonic'],'unlock_swipes':1,'home_after_approval':1,'icon_clicks':1,'cleanup_restore':1,'cleanup_unlock':1,'review_elapsed':consumed['elapsed'],'observed_lock_ids':flags['lock_ids']}
with (HERE/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
