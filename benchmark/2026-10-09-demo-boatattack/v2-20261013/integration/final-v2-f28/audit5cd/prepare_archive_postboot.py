"""Prepare one reviewed audit-tree rename; offline only. No transport invocation."""
import argparse,hashlib,json,os,re,shlex,uuid
from pathlib import Path
ROOT='/data/westlake-demo/u13/boat-v2-20261013-r4'
SERIAL='5cd1e3dd00000000000000000923012c'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(p):return Path(os.path.expandvars(str(p))).resolve()
def portable(p):return '$WORKSPACES/'+str(Path(p).resolve().relative_to(resolve(os.environ['WORKSPACES'])))
def ref(p):return dict(path=portable(p),sha256=sha(p))
def q(s):return shlex.quote(str(s))
def validate_fresh(fresh,boot,rows,dirs,cfg,uid):
 receipt=read(fresh/'receipt.json');raw=(fresh/'stdout.txt').read_text();err=(fresh/'stderr.txt').read_bytes()
 need(receipt['rc']==0 and receipt['device_writes']==0 and not err,'fresh read failed')
 need(receipt['argv'][1:3]==['-t',SERIAL],'fresh serial')
 lines=raw.splitlines()
 need(lines[-1]=='AUDIT_READ_RC=0','fresh remote rc')
 def section(a,b):
  need(lines.count(a)==1 and lines.count(b)==1,'fresh section identity')
  return lines[lines.index(a)+1:lines.index(b)]
 need(section('BOOT_BEFORE','TREE')==[boot] and [v for v in section('BOOT_AFTER','AUDIT_READ_RC=0') if v]==[boot],'fresh bookend boot')
 need(section('TREE','IDENTITIES')==sorted(x['target'] for x in rows+dirs),'fresh exact7 tree')
 entries=section('IDENTITIES','CFG');seen={};i=0
 while i<len(entries):
  need(entries[i].startswith('TARGET='),'fresh target record');target=entries[i][7:];need(target not in seen,'duplicate target')
  meta=entries[i+1];i+=2;digest=None
  if i<len(entries) and not entries[i].startswith('TARGET='):
   parts=entries[i].split();need(len(parts)==2 and parts[1]==target,'fresh SHA target');digest=parts[0];i+=1
  seen[target]=(meta,digest)
 for row in rows+dirs:
  meta,digest=seen[row['target']];prefix=':'.join(str(row[k]) for k in ('mode','uid','gid','label'))+':'
  need(meta.startswith(prefix) and re.fullmatch(r'[0-9]+:[0-9]+',meta[len(prefix):]),'fresh metadata')
  if 'sha256' in row:need(digest==row['sha256'],'fresh audit SHA')
  else:need(digest is None and meta[len(prefix):]==row['identity'],'fresh directory inode')
 need(section('CFG','PROCESSES')==[cfg['before']['sha256']+'  '+cfg['target']],'fresh cfg')
 procs=section('PROCESSES','SELF_MOUNTINFO');need(procs[0].split()==['PID','PPID','UID','NAME'],'fresh ps header')
 for line in procs[1:]:
  fields=line.split();need(len(fields)>=4 and all(v.isdigit() for v in fields[:3]) and int(fields[2])!=uid,'fresh consumer/ps')
 for a,b in [('SELF_MOUNTINFO','INIT_MOUNTINFO'),('INIT_MOUNTINFO','BOOT_AFTER')]:
  mounts=section(a,b);need(bool(mounts),'fresh empty mounts')
  for line in mounts:
   fields=line.split();need(len(fields)>6 and fields[4]!=ROOT and not fields[4].startswith(ROOT+'/'),'fresh owned mount')
 return [fresh/'receipt.json',fresh/'stdout.txt',fresh/'stderr.txt']
def build(run,out,capture,fresh):
 run=run.resolve();plan_path=run/'plan.enabled.json';p=read(plan_path);tx=read(run/'transaction/transaction.json');closed=read(run/'closed.json');r5=read(run/'restored-r5.json');br=read(run.parent/'board-run/board-run-result.json')
 need(p['serial']==SERIAL and tx['plan_sha256']==sha(plan_path),'transaction identity')
 cap=read(capture);boot=cap['boot_after'];candidate=read(run/'candidate-boot-result.json');returned=read(run/'baseline-return-boot-result.json')
 need(cap['serial']==SERIAL and cap['boot_before']==boot and cap['complete'] is False and cap['root_absent']==dict(target=ROOT,exists=True) and cap['boat_uid']==p['boat_uid'],'actual current incomplete-root capture')
 need(returned['ready'] is True and returned['boot_id']==boot and candidate['boot_id']!=boot,'actual return boot')
 need(closed['status']=='RESTORED_PENDING_VISUAL_REVIEW' and closed['serial']==SERIAL and closed['boot_id']==boot,'restoration closure/current boot')
 need(br.get('before_unlock')==0 and br.get('after_lock')==2 and not br.get('before_unlock_error'),'window not closed')
 need((run/'candidate-boot-intent.json').is_file() and (run/'baseline-return-boot-intent.json').is_file(),'postboot restoration intents required')
 need(r5['status']=='PASS' and r5['passed'] is True and r5['file_count']==940 and r5['synthetic'] is False and r5['mode']=='live-readonly','actual restored940 required')
 need(r5['serial']==SERIAL and r5['current_boot']==r5['boot_before']==r5['boot_after']==boot,'R5 sameboot')
 need(len(r5['checks'])==940 and all(x['equal'] is True and x['actual']==x['expected'] for x in r5['checks']),'R5 exact files')
 rollbacks=list((run/'transaction').glob('rollback-*.json'));need(len(rollbacks)==1,'one exact rollback required');rp=rollbacks[0];r=read(rp)
 need(r['state']=='RESTORED_RETAINED_AUDIT_VERIFIED' and r['success'] is True and r['baseline319_equal'] is True and r['files_and_binds_restored'] is True,'rollback not complete')
 need(r['retained_directories']==p['directories'] and {d['target'] for d in p['directories']}=={ROOT,ROOT+'/sources'},'directory set differs')
 rows=r['retained_audit'];cfg=p['members'][-1];allowed={ROOT+'/cfg-stage-'+cfg['sha256'],ROOT+'/cfg-stage-'+cfg['before']['sha256']}
 allowed |= {ROOT+'/boat-'+candidate['boot_id']+'.'+suffix for suffix in ('log','intents','receipt')}
 need({x['target'] for x in rows}==allowed and len(rows)==5,'exact2 cfg stages and3 candidate boot audit files only')
 paths=[plan_path,run/'transaction/transaction.json',rp,run/'closed.json',run/'restored-r5.json',run.parent/'board-run/board-run-result.json',capture,run/'candidate-boot-result.json',run/'baseline-return-boot-result.json',run/'candidate-boot-intent.json',run/'baseline-return-boot-intent.json'];dirs=[]
 for i,d in enumerate(p['directories']):
  journal=run/'transaction'/('directory-created-%03d.json'%i);j=read(journal);paths.append(journal)
  need(j['plan_sha256']==sha(plan_path) and j['target']==d['target'] and j['after']==d['after'] and re.fullmatch(r'[0-9]+:[0-9]+',j['identity']),'directory journal drift')
  dirs.append(dict(target=d['target'],identity=j['identity'],**d['after']))
 for row in rows:
  need(row['exists'] is True and re.fullmatch('[a-f0-9]{64}',row['sha256']) and (not row['target'].split('/')[-1].startswith('cfg-stage-') or row['sha256']==row['target'].rsplit('-',1)[1]),'audit SHA identity')
  need({k:row[k] for k in ['mode','uid','gid','label']}==dict(mode='644',uid=0,gid=0,label='u:object_r:data_file:s0'),'audit metadata')
 paths += validate_fresh(fresh,boot,rows,dirs,cfg,p['boat_uid'])
 archive=str(Path(ROOT).parent/('boat-audit-r5-return-'+uuid.uuid4().hex))
 mapping=dict(schema='boat-owned-audit-archive/v1',serial=SERIAL,boot_id=boot,source=ROOT,destination=archive,files=rows,directories=dirs,evidence=[ref(f) for f in paths],operation='same-parent-rename',recursive_delete=False,device_calls=0)
 lines=['#!/system/bin/sh','set -eu','export LC_ALL=C',f'ROOT={q(ROOT)}',f'ARCHIVE={q(archive)}',f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}', 'test ! -e "$ARCHIVE"; test ! -L "$ARCHIVE"', 'walk="$ROOT"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done', 'test "$(stat -c %d "$ROOT")" = "$(stat -c %d "$(dirname "$ROOT")")"',f'test "$(sha256sum {q(cfg["target"])} | cut -d" " -f1)" = {q(cfg["before"]["sha256"])}']
 lines += 'set -f\nprocesses=$(ps -A -o PID,PPID,UID,NAME)\nprintf \'%s\\n\' "$processes" | {\n first=1\n while read -r apid appid auid aname; do\n  if [ "$first" = 1 ]; then test "$apid:$appid:$auid" = PID:PPID:UID; first=0; continue; fi\n  for number in "$apid" "$appid" "$auid"; do case "$number" in \'\'|*[!0-9]*) exit 1;; esac; done\n  test "$auid" != 20011301\n done\n test "$first" = 0\n}\nfor table in /proc/self/mountinfo /proc/1/mountinfo; do\n while IFS= read -r mountrow; do\n  set -- $mountrow\n  test "$#" -gt 6\n  case "$5" in "$ROOT"|"$ROOT"/*) exit 1;; esac\n done < "$table"\ndone\n'.replace('20011301',str(p['boat_uid'])).splitlines()
 def verify(base,after=False):
  entries=sorted([x['target'].replace(ROOT,base,1) for x in dirs+rows]);commands=[f'actual=$(find {q(base)} -print | sort)',f'test "$actual" = {q(chr(10).join(entries))}']
  for d in dirs:
   target=d['target'].replace(ROOT,base,1);want=':'.join(str(d[k]) for k in ['mode','uid','gid','label'])+':'+d['identity'];commands += [f'test ! -L {q(target)}; test -d {q(target)}',f'test "$(stat -c %a:%u:%g:%C:%d:%i {q(target)})" = {q(want)}']
  for i,row in enumerate(rows):
   target=row['target'].replace(ROOT,base,1);want=':'.join(str(row[k]) for k in ['mode','uid','gid','label']);commands += [f'test ! -L {q(target)}; test -f {q(target)}',f'test "$(stat -c %a:%u:%g:%C {q(target)})" = {q(want)}',f'test "$(sha256sum {q(target)} | cut -d" " -f1)" = {q(row["sha256"])}']
   commands += [f'test "$(stat -c %d:%i {q(target)})" = "$inode{i}"'] if after else [f'inode{i}=$(stat -c %d:%i {q(target)})']
  return commands
 lines+=verify(ROOT)+['# Only mutation: same-parent rename of the fully owned audit tree.','mv "$ROOT" "$ARCHIVE"','test ! -e "$ROOT"; test ! -L "$ROOT"']+verify(archive,True)
 lines += [f'printf \'%s\\n\' {q(json.dumps(dict(status="ARCHIVED_VERIFIED",source=ROOT,destination=archive,boot_id=boot,original_root_absent=True),separators=(",",":")))}']
 need(not out.exists(),'fresh local output required');out.mkdir(parents=True);remote=out/'remote.sh';remote.write_text('\n'.join(lines)+'\n');mapping['remote_sha256']=sha(remote);(out/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
 lock=p['tools']['lock'];hdc=p['hdc']
 # Host wrapper checks each journal pin and the native lock protocol, then makes ONE HDC call.
 host=['#!/bin/bash','set -euo pipefail','HERE=$(cd -- "$(dirname -- "$0")" && pwd)','if [ "${1:-}" != --execute ]; then cat "$HERE/mapping.json"; exit 0; fi',': "${WORKSPACES:?}" "${HOLDER:?owner-only lock holder required}"',f'LOCK="{lock["path"]}"',f'test "$(shasum -a 256 "$LOCK" | cut -d" " -f1)" = {q(lock["sha256"])}',f'test "$(shasum -a 256 "$HERE/remote.sh" | cut -d" " -f1)" = {q(sha(remote))}']
 for e in mapping['evidence']:host += [f'test "$(shasum -a 256 "{e["path"]}" | cut -d" " -f1)" = {q(e["sha256"])}']
 wrapped='sh -c '+q(remote.read_text())+'; archive_rc=$?; printf "\\nARCHIVE_REMOTE_RC=%s\\n" "$archive_rc"'
 (out/'command.txt').write_text(wrapped)
 host += ['LOG=$(mktemp -d "$HERE/execution.XXXXXX")', 'date -u > "$LOG/started.txt"', 'check_held(){', ' local text err; err=$(mktemp "$LOG/held.XXXXXX")', ' text=$(bash "$LOCK" held '+q(SERIAL)+' 2>"$err") || return 1', ' test ! -s "$err" || return 1', ' local owner pid stamp extra; read -r owner pid stamp extra <<< "$text"', ' test "$owner" = "$HOLDER"; [[ "$pid" =~ ^[0-9]+$ ]]; test -n "$stamp"; test -z "$extra"', ' test "$(printf \'%s\\n\' "$text" | wc -l | tr -d \' \')" = 1', ' printf "%s" "$text"','}', 'held=$(check_held)', 'printf "%s\\n" "$held" > "$LOG/held.txt"', 'test "$(check_held)" = "$held"', f'test "$(shasum -a 256 "$HERE/command.txt" | cut -d" " -f1)" = {q(sha(out/"command.txt"))}', f'if {q(hdc)} -t {q(SERIAL)} shell "$(cat "$HERE/command.txt")" > "$LOG/stdout" 2> "$LOG/stderr"; then trc=0; else trc=$?; fi', 'printf "%s\\n" "$trc" > "$LOG/transport-rc.txt"', 'date -u > "$LOG/finished.txt"', 'cat "$LOG/stdout"; cat "$LOG/stderr" >&2', 'test "$trc" = 0', 'test ! -s "$LOG/stderr"', 'test "$(tail -n 1 "$LOG/stdout" | tr -d \'\\r\')" = ARCHIVE_REMOTE_RC=0', f'grep -Fx {q(json.dumps(dict(status="ARCHIVED_VERIFIED",source=ROOT,destination=archive,boot_id=boot,original_root_absent=True),separators=(",",":")))} "$LOG/stdout"', 'test "$(check_held)" = "$held"', 'printf \'%s\\n\' ARCHIVE_HOST_AND_REMOTE_VERIFIED > "$LOG/result.txt"']
 (out/'archive.sh').write_text('\n'.join(host)+'\n');return mapping
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--capture',type=Path,required=True);ap.add_argument('--fresh-audit',type=Path,required=True);a=ap.parse_args()
 try:m=build(a.run,a.out,a.capture,a.fresh_audit);print(json.dumps(dict(status='PREPARED_NOT_EXECUTED',files=len(m['files']),directories=len(m['directories']),remote_sha256=m['remote_sha256'],device_calls=0)))
 except (OSError,ValueError,KeyError,TypeError) as e:print('REFUSE '+str(e));raise SystemExit(2)
