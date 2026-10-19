#!/usr/bin/env python3
"""Bounded offline audit of an existing hilog capture; never invokes HDC."""
from pathlib import Path
import collections,datetime,hashlib,json,re
from zoneinfo import ZoneInfo
O=Path(__file__).resolve().parent;S=Path.home()/'.local/share/westlake/toutiao-resume-20261019';P=S/'video-r4-play-state';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j=lambda p:json.loads(p.read_text())
raw=(P/'hilog-child.txt').read_text();lines=raw.splitlines();rx=re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+(\d+)\s+([A-Z])\s+(\S+): (.*)$');rows=[rx.match(l).groups() for l in lines];assert len(rows)==62413 and all(x[1]=='9360' for x in rows)
cmd=j(P/'commands/command-00007.json');assert cmd['exit_code']==0 and cmd['argv'][-1].startswith('hilog -x -P 9360;')
full=(P/'commands/command-00007.stdout.txt').read_text();assert '__BMS_REMOTE_RC_577473406c0143f2af45aee18fe234ac__0' in full and full.split('\n__BMS_REMOTE_RC_')[0].rstrip('\n')==raw.rstrip('\n')
for i in ['00006','00010']:
 assert (P/'commands'/('command-'+i+'.stdout.txt')).read_text().splitlines()[0]=='fade993a-5649-44c5-9677-79f6ee82a8ad'
stat=(P/'process.stat').read_text();fields=stat.split(') ',1)[1].split();assert fields[1]=='6696' and fields[19]=='18882'
counts={n:sum(n in l for l in lines) for n in ['TTVideoEngine','DataLoaderHelper','VideoPlayerImpl','ttmplayer','TTPlayer','MediaCodec','avmdl']};assert counts['avmdl']==36 and all('MUSL-LDSO' in l for l in lines if 'avmdl' in l)
records=[]
for n in ['video-r4-play1','video-r4-center-tap','video-r4-swipe-next']:
 p=S/n/'record.json';d=j(p);assert d['child']=='9360' and d['child_birth']=='18882'
 records.append({'run':n,'record_sha256':h(p),'tap_time_host_plus08':datetime.datetime.fromtimestamp(d['tap_completed_at'],ZoneInfo('Asia/Shanghai')).isoformat()})
files=[P/'hilog-child.txt',P/'process.stat']+[p for p in (P/'commands').glob('*') if p.is_file()]
d={'token':'video-1919-observability','correction':'Existing same-child hilog WAS collected; do not describe it as never captured.','capture':{'argv_shell':cmd['argv'][-1],'transport_rc':0,'explicit_remote_rc':0,'stderr_bytes':(P/'commands/command-00007.stderr.txt').stat().st_size,'bytes':(P/'hilog-child.txt').stat().st_size,'sha256':h(P/'hilog-child.txt'),'line_count':len(lines),'first_record':rows[0][0],'last_record':rows[-1][0],'all_record_pid':9360,'boot_bookends':'fade993a-5649-44c5-9677-79f6ee82a8ad','process_stat_after_capture':{'pid':9360,'ppid':6696,'birth':18882,'state':fields[0]},'priority_counts':dict(collections.Counter(x[3] for x in rows)),'explicit_priority_option':False,'effective_default_filter':'unknown; no D/V/F records is not proof all priorities were enabled'},'matching_case_sensitive_lines':counts,'avmdl':'36 MUSL-LDSO load/header failures; no causal playback conclusion','error_tags':dict(collections.Counter(x[4] for x in rows if x[3]=='E')),'new_player_exception_identified':False,'events':records,'coverage':'By displayed local log timestamps vs recorded host epoch (+08), retained log begins about10s after first tap, includes center tap, and ends before swipe. Not a full launch-to-all-observations trace; exact device-host clock calibration is not supplied here.','absence_limits':['Tagged method/logger may be filtered or delegated under another tag','No exact Java logger-default or current Log JNI-provider proof','Native true is not Java logger-enablement evidence','No new playback/root-cause inference'],'source_files':[{'path':'$HOME/'+str(p.relative_to(Path.home())),'sha256':h(p),'bytes':p.stat().st_size} for p in files],'device_calls':0}
(O/'results.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'lines':len(lines),'counts':counts,'priorities':d['capture']['priority_counts'],'status':'EXISTING_CAPTURE_CONFIRMED_LIMITED_COVERAGE'},indent=2))
