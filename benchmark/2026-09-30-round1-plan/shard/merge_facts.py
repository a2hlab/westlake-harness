#!/usr/bin/env python3
"""Read-only shard merge. Missing evidence is unknown, never a fabricated zero.

Reuses the UID/table and captured-field method of scripts/lab/run_facts.py;
additionally excludes named same-UID helpers and audits the planned partition.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from shard_plan import dump, run_base, sha

HASH = re.compile(r'^([0-9a-f]{64})\s+(/\S+)\s*$')


def fingerprint(path):
    rows={}
    for line in path.read_text().splitlines():
        if not line.strip():continue
        match=HASH.fullmatch(line.strip())
        if not match:raise ValueError('invalid fingerprint row: '+str(path))
        digest,name=match.groups()
        if name in rows and rows[name]!=digest:raise ValueError('conflicting fingerprint path')
        rows[name]=digest
    if not rows:raise ValueError('empty fingerprint')
    return rows


def processes(path, uid, package):
    if uid is None or not path.is_file():return {'alive':None,'reason':'missing UID or process table','pids':[]}
    lines=path.read_text().splitlines();header=lines[0].split() if lines else []
    if not {'UID','PID','NAME'}<=set(header):return {'alive':None,'reason':'unrecognized process header','pids':[]}
    ui,pi,ni=(header.index(x) for x in ['UID','PID','NAME']);found=[];helpers=[]
    for number,line in enumerate(lines[1:],2):
        values=line.split()
        if len(values)<=ui:continue
        if values[ui]!=str(uid):continue
        if len(values)<=max(ui,pi,ni) or not values[pi].isdigit():return {'alive':None,'reason':'malformed target UID row','pids':[]}
        item=dict(pid=values[pi],name=values[ni],line=number)
        is_app=values[ni]=='appspawn-x' or bool(package and (values[ni]==package or values[ni].startswith(package+':')))
        (found if is_app else helpers).append(item)
    return dict(alive=bool(found),pids=found,same_uid_helpers=helpers,source=str(path),sha256=sha(path))


def record_facts(path):
    r=json.loads(path.read_text())
    if not isinstance(r,dict) or not isinstance(r.get('key'),str):raise ValueError('invalid record object: '+str(path))
    shots=r.get('screenshots')
    valid=isinstance(shots,list) and all(isinstance(s,dict) and isinstance(s.get('captured'),bool) for s in shots)
    procs={stage:processes(path.parent/('processes-'+stage+'.txt'),(r.get('bms') or {}).get('uid'),r.get('package')) for stage in ('t5','t20')}
    return dict(key=r['key'],record=str(path),record_sha256=sha(path),serial=r.get('serial'),boot_id=r.get('boot_id'),
                apk_sha256=r.get('apk_sha256'),finished=r.get('finished_at') is not None,
                captured=sum(s['captured'] is True for s in shots) if valid else None,
                slots=len(shots) if isinstance(shots,list) else None,
                processes=procs,alive_t5=procs['t5']['alive'],alive_t20=procs['t20']['alive'],
                status=r.get('status'),lit=None,runtime_fingerprint=r.get('runtime_fingerprint'))


def missing(key, shard, reason):
    return dict(key=key,shard=shard,record=None,captured=None,slots=None,alive_t5=None,alive_t20=None,finished=False,lit=None,status='unknown',reason=reason)


def validate_partition(plan):
    expected=plan['expected_keys'];shards=plan['shards'];flat=[k for s in shards for k in s['keys']]
    if len(set(expected))!=len(expected) or len(set(flat))!=len(flat) or set(flat)!=set(expected):raise ValueError('partition is not a disjoint cover')
    if len(shards)!=3 or len({s['name'] for s in shards})!=3 or len({s['serial'] for s in shards})!=3:raise ValueError('exactly three distinct shards/boards required')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']) for s in shards):raise ValueError('unsafe shard name')


def merge(plan, bindings, expected_fingerprint=None):
    validate_partition(plan)
    if set(bindings)-{s['name'] for s in plan['shards']}:raise ValueError('unknown shard binding')
    rows=[];audit=[];errors=[];raw_facts={};maps=[]
    for shard in plan['shards']:
        name=shard['name'];raw=bindings.get(name);base=None
        if raw is not None and Path(raw).exists():base=run_base(Path(raw))
        a=dict(name=name,run=str(base) if base else None,serial=shard['serial'],profile=None,baseline=None,frozen_check=None)
        audit.append(a)
        if base is None:
            rows.extend(missing(k,name,'shard not supplied or directory missing') for k in shard['keys']);continue
        fp=base/'runtime-fingerprint.txt';facts=base/'facts.txt';baseline=base/'baseline.json'
        try:
            if fp.is_file():
                a['profile']=fingerprint(fp);maps.append(a['profile']);a['fingerprint_file_sha256']=sha(fp)
                a['runtime_short']=hashlib.sha256(fp.read_text().strip().encode()).hexdigest()[:12]
            if facts.is_file():
                raw_facts[name]=facts.read_bytes().decode('utf-8');a['facts_sha256']=sha(facts)
                first=raw_facts[name].splitlines()[0] if raw_facts[name] else ''
                m=re.match(r'RUNTIME fingerprint=([0-9a-f]{12}) files=(\d+)',first)
                if a['profile'] and (not m or m[1]!=a['runtime_short'] or int(m[2])!=len(a['profile'])):errors.append(name+':facts fingerprint header mismatch')
                frozen=re.search(r'^FROZEN checked=(\d+) violations=(\d+)',raw_facts[name],re.M)
                if frozen:
                    a['frozen_check']={'checked':int(frozen[1]),'violations':int(frozen[2])}
                    if int(frozen[2]):errors.append(name+':frozen violations')
            if baseline.is_file():
                a['baseline']=json.loads(baseline.read_text());a['baseline_sha256']=sha(baseline)
                if not isinstance(a['baseline'],dict):a['baseline']=None;raise ValueError('invalid baseline object')
                if a['profile'] and a['baseline'].get('runtime_fingerprint')!=a['runtime_short']:errors.append(name+':baseline fingerprint mismatch')
        except (ValueError,OSError) as exc:errors.append(name+':'+str(exc))
        observed={}
        for path in sorted(base.glob('*/record.json')):
            try:
                row=record_facts(path);key=row['key']
                if key in observed:raise ValueError('duplicate record key '+key)
                if key not in shard['keys']:raise ValueError('record belongs to another/no shard: '+key)
                if path.parent.name!=key:raise ValueError('record directory/key mismatch: '+key)
                if row['serial']!=shard['serial']:raise ValueError('wrong record serial: '+key)
                expected_sha=plan.get('expected_apk_sha256',{}).get(key)
                if expected_sha and row['apk_sha256']!=expected_sha:raise ValueError('APK mismatch: '+key)
                if a['baseline'] and row['boot_id']!=a['baseline'].get('boot_id'):raise ValueError('record boot mismatch: '+key)
                if row['runtime_fingerprint'] and row['runtime_fingerprint']!=a.get('runtime_short'):raise ValueError('per-record runtime mismatch: '+key)
                row['shard']=name;observed[key]=row
            except (ValueError,KeyError,TypeError,OSError) as exc:errors.append(name+':'+str(exc))
        rows.extend(observed.get(k,missing(k,name,'record missing, corrupt or rejected; see errors')) for k in shard['keys'])
    if maps and any(m!=maps[0] for m in maps[1:]):errors.append('mixed measured runtime profiles')
    if expected_fingerprint and any(m!=expected_fingerprint for m in maps):errors.append('measured profile differs from expected release')
    known={};unknown={};totals={}
    for metric in ('captured','slots','alive_t5','alive_t20'):
        unknown[metric]=sum(r[metric] is None for r in rows)
        known[metric]=sum(r[metric] for r in rows if r[metric] is not None)
        totals[metric]=known[metric] if not unknown[metric] else None
    complete=all(r['record'] and r['finished'] for r in rows)
    metadata_complete=all(a['profile'] and a['baseline'] and a['baseline'].get('boot_id') for a in audit)
    frozen_verified=all(a['frozen_check'] and a['frozen_check']['checked']>0 and a['frozen_check']['violations']==0 for a in audit)
    status='invalid' if errors else 'partial' if not complete else 'complete'
    eligible=status=='complete' and metadata_complete and frozen_verified and expected_fingerprint is not None
    report=dict(status=status,expected_keys=len(rows),records_present=sum(r['record'] is not None for r in rows),
                completed_records=sum(r['record'] is not None and r['finished'] for r in rows),
                observed_totals=known,unknown_key_counts=unknown,totals=totals,errors=errors,
                present_profiles_uniform=bool(maps) and all(m==maps[0] for m in maps),
                profile_metadata_complete=metadata_complete,expected_release_bound=expected_fingerprint is not None,
                frozen_checks_verified=frozen_verified,u1_same_profile_score_eligible=eligible,
                lighting='unknown; outer screenshot signatures required',shards=audit,rows=rows,
                caveat='Counts are captured flags and UID/name process table observations, not UI or image-hash verification. Fingerprints are producer snapshots, not continuous per-app measurement. Unknown samples never become zero.')
    return report,raw_facts


def format_facts(report):
    def show(v):return 'unknown' if v is None else 'yes' if v is True else 'no' if v is False else str(v)
    lines=['MERGE status='+report['status']+' U1_profile_eligible='+str(report['u1_same_profile_score_eligible']).lower()]
    for r in report['rows']:
        lines.append(f"{r['key']:<22} shard={r['shard']} captured={show(r['captured'])}/{show(r['slots'])} alive_t5={show(r['alive_t5'])} alive_t20={show(r['alive_t20'])}")
    lines.append('TOTAL expected_keys='+str(report['expected_keys'])+' records_present='+str(report['records_present']))
    lines.append('OBSERVED '+json.dumps(report['observed_totals'],sort_keys=True))
    lines.append('UNKNOWN_KEYS '+json.dumps(report['unknown_key_counts'],sort_keys=True))
    lines.append('FULL_TOTALS '+json.dumps(report['totals'],sort_keys=True))
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--shard',action='append',default=[])
    p.add_argument('--expected-fingerprint',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=json.loads(a.plan.read_text());bindings={}
    for item in a.shard:
        name,sep,value=item.partition('=')
        if not sep or not value or name in bindings:raise ValueError('use unique NAME=/explicit/run bindings')
        bindings[name]=Path(value)
    for s in plan['shards']:
        if sha(a.plan.parent/s['keys_file'])!=s['keys_sha256']:raise ValueError('keys file modified: '+s['name'])
    report,raw=merge(plan,bindings,fingerprint(a.expected_fingerprint) if a.expected_fingerprint else None)
    report['plan_sha256']=sha(a.plan);report['script_sha256']=sha(Path(__file__))
    if a.out.exists():raise ValueError('use a fresh output directory')
    a.out.mkdir(parents=True);(a.out/'source-facts').mkdir()
    for name,text in raw.items():(a.out/'source-facts'/(name+'.txt')).write_text(text)
    dump(a.out/'results.json',report);(a.out/'facts.txt').write_text(format_facts(report))
    print('\n'.join(format_facts(report).splitlines()[-4:]))
    return 1 if report['errors'] else 0


if __name__=='__main__':raise SystemExit(main())
