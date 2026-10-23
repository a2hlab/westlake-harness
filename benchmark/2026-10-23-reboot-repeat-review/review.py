#!/usr/bin/env python3
"""Offline receipt review. Never executes recorded commands. --capture freezes input membership."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--main', type=Path, required=True)
p.add_argument('--private-root', type=Path, default=Path.home()/'.local/share/westlake')
p.add_argument('--capture', action='store_true')
a = p.parse_args()
roots = {'T108': a.private_root/'spare-board-boot-entry-20261023', 'T109': a.private_root/'spare-board-reboot-repeat-20261023', 'MAIN': a.main}
def sha(b): return hashlib.sha256(b).hexdigest()
idxpath = HERE/'input-index.json'
if a.capture:
    pins = []
    for card in ('T108','T109'):
        root = roots[card]
        selected = set((root/'raw').rglob('*.argv')) if root.exists() else set()
        for sub in ['00','01','02','05','06']:
            d = root/'raw'/sub
            if d.exists(): selected.update(x for x in d.iterdir() if x.is_file())
        for n in ['raw/OLD_BOOT','raw/NEW_BOOT','raw/LOCK_EPOCH','raw/03/pw.stdout','run/facts.txt']:
            if (root/n).is_file(): selected.add(root/n)
        selected.update(root.glob('run/*/record.json'))
        for f in sorted(selected):
            b=f.read_bytes(); pins.append(dict(root=card,path=str(f.relative_to(root)),sha256=sha(b),bytes=len(b)))
    for n in ['scripts/lab/run_facts.py','benchmark/2026-10-23-spare-board-boot-entry/outer-review.json']:
        b=(a.main/n).read_bytes();pins.append(dict(root='MAIN',path=n,sha256=sha(b),bytes=len(b)))
    idxpath.write_text(json.dumps(pins,indent=2)+'\n')
pins=json.loads(idxpath.read_text()); data={}
for pin in pins:
    b=(roots[pin['root']]/pin['path']).read_bytes()
    if sha(b)!=pin['sha256'] or len(b)!=pin['bytes']: raise ValueError('Input changed: '+pin['root']+'/'+pin['path'])
    data[pin['root'],pin['path']]=b

def text(card,n):
    b=data.get((card,n));return b.decode(errors='replace').strip() if b is not None else None

def receipt(card,stem):
    vals={x:text(card,'raw/'+stem+'.'+x) for x in ['argv','start','end','rc','stdout','stderr']}
    if any(v is None for v in vals.values()):return dict(ref='raw/'+stem,status='pending_incomplete_receipt')
    return dict(ref='raw/'+stem,status='complete',rc=int(vals['rc']),start=float(vals['start'].split()[0]),end=float(vals['end'].split()[0]),stdout=vals['stdout'],stderr_bytes=len(data[card,'raw/'+stem+'.stderr']))

out={'scope':'Offline receipts only; software reboot, not physical power; no cause attribution','runs':{},'author_commit':None}
for card in ['T108','T109']:
    commands=[]
    for (c,n),b in data.items():
        if c==card and n.endswith('.argv'):
            cmd=json.loads(b)
            if 'shell' in cmd:
                s=cmd[-1]
                if s=='reboot' or re.fullmatch(r'uitest uiInput click \d+ \d+',s):commands.append((n,s))
    r={'status':'partial_receipts_reviewed','old_boot':text(card,'raw/OLD_BOOT'),'new_boot':text(card,'raw/NEW_BOOT'),'reboot_command_count':sum(s=='reboot' for _,s in commands),'click_command_count':sum(s!='reboot' for _,s in commands),'reboot':receipt(card,'01/reboot'),'click':receipt(card,'05/click'),'samples':[]}
    r['boot_changed']=bool(r['old_boot'] and r['new_boot'] and r['old_boot']!=r['new_boot'])
    r['boot_receipt_refs']=[n for (c,n),b in data.items() if c==card and n.startswith('raw/01/b') and n.endswith('.stdout') and r['new_boot'] and r['new_boot'].encode() in b]
    r['new_boot_evidenced']=r['boot_changed'] and any(receipt(card,n[4:-7]).get('rc')==0 for n in r['boot_receipt_refs'])
    r['click_body_no_error']=r['click'].get('rc')==0 and r['click'].get('stdout')=='No Error'
    for t in [10,30,60,90,120]:
        shot=receipt(card,f'05/s{t}_shot');recv=receipt(card,f'05/s{t}_rs');n=f'raw/05/s{t}.jpeg';b=data.get((card,n))
        item={'label':f't{t}','shot':shot,'recv_rc':recv.get('rc'),'status':'pending'}
        if b is not None and shot.get('rc')==0 and recv.get('rc')==0:
            item.update(status='captured',sha256=sha(b),bytes=len(b))
            if r['click'].get('status')=='complete':item['relative_to_click_interval_s']=[round(shot['start']-r['click']['end'],6),round(shot['end']-r['click']['start'],6)]
        r['samples'].append(item)
    records=[(n,json.loads(b)) for (c,n),b in data.items() if c==card and n.endswith('/record.json')]
    r['facts_status']='pending_record'
    if records:
        record=records[0][1];shots=record.get('screenshots',[])
        for s in shots:
            actual=next(x for x in r['samples'] if x['label']==s['label'])
            if s['captured'] and (actual['status']!='captured' or s['sha256']!=actual['sha256'] or s['bytes']!=actual['bytes']):raise ValueError('Record mismatch')
        # This supplied helper is read-only; only this host Python command is executed.
        proc=subprocess.run([sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(roots[card]/'run')],capture_output=True,text=True)
        if proc.returncode:raise ValueError('facts helper failed')
        r['facts_verbatim']=proc.stdout.splitlines();r['facts_equal']=proc.stdout.strip()==text(card,'run/facts.txt');r['facts_status']='recomputed'
        if not r['facts_equal']:raise ValueError('facts mismatch')
    r['restore']={k:receipt(card,'06/'+k) for k in ['pr','po','pw','tmp']}
    r['restore']['preimage_power']=text(card,'raw/03/pw.stdout')
    r['restore']['unlock_time_label']=text(card,'raw/06/UNLOCK_T')
    r['restore']['unlock_out']=text(card,'raw/06/unlock.out')
    r['restore']['held_out']=text(card,'raw/06/held.out')
    r['restore']['held_rc']='unknown: no separate raw rc receipt in selected directory'
    r['restore']['limitation']='Timeout values can match while AWAKE differs from preimage SLEEP; empty held/unlock output alone does not prove rc.'
    r['lock_epoch']=text(card,'raw/LOCK_EPOCH')
    r['status']='receipts_reviewed_visual_attributed' if r['facts_status']=='recomputed' and r['restore']['pw'].get('rc')==0 else 'pending_completion'
    out['runs'][card]=r
outer=json.loads(data['MAIN','benchmark/2026-10-23-spare-board-boot-entry/outer-review.json'])
out['T108_visual_existing_outer_review']=outer
out['T108_first_positive_sample']='t60, attributed to existing outer/sentry review; not independently re-viewed or exact first frame'
out['continuity']=out['runs']['T108']['new_boot']==out['runs']['T109']['old_boot'] if out['runs']['T109']['old_boot'] else None
out['comparison']='T109 pending; do not infer repeat success/failure before completed receipts and visual review'
out['pinned_files']=len(pins)
print(json.dumps(out,indent=2))
