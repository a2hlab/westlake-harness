"""Extract separate consent/article timings from archived logs, never activity substrings."""
import argparse,json,re
from pathlib import Path


def stamps(text):
    return [float(x) for x in re.findall(r'^(\d+\.\d+)\s+\d',text or '',re.M)]


def analyze(root):
    r=json.loads((root/'result.json').read_text())
    events=[];open_events={};lifecycle=[];fatal=[];images=[];rejects=[];activity_times=[]
    with (root/'child.stderr').open(errors='replace') as f:
        for number,line in enumerate(f,1):
            m=re.match(r'\[ABILITY38-DISPATCH\] phase=begin seq=(\d+) uptime=(\d+) queueMs=(\d+).*action=ACTION_(DOWN|UP).*eventTime=(\d+)',line)
            if m:
                seq,begin,queue,action,event=m.groups()
                item=dict(line=number,seq=int(seq),begin_ms=int(begin),queue_ms=int(queue),action=action,event_ms=int(event))
                events.append(item);open_events[seq]=item
            m=re.match(r'\[ABILITY38-DISPATCH\] phase=end seq=(\d+) uptime=(\d+)',line)
            if m and m[1] in open_events:
                item=open_events.pop(m[1]);item['dispatch_ms']=int(m[2])-item['begin_ms']
            if re.match(r'\[B47-SLA\] ENTRY .*ability=com\.ss\.android\.detail\.feature\.detail2\.view\.NewDetailActivity\b',line):
                lifecycle.append(dict(line=number,text=line.strip()))
            if re.match(r'\[ABILITY38-(START|RESUMED)\]',line):activity_times.append(dict(line=number,text=line.strip()))
            if 'Fatal signal' in line:fatal.append(dict(line=number,text=line.strip()))
            if '[IMG] Loaded ' in line and 'toutiao.art' in line:images.append(dict(line=number,text=line.strip()))
            if any(k in line for k in ['ClassLoaderContext classpath', 'checksum mismatch', 'Could not check odex file']):
                rejects.append(dict(line=number,text=line.strip()))
    touch=stamps(r.get('touch'));consent=stamps(r.get('consent'))
    last=stamps((r.get('consent_inputs') or [r.get('consent')])[-1])
    select=lambda ts:[e for e in events if ts and ts[0]-.1<=e['event_ms']/1000<=ts[-1]+.2]
    maps=[]
    for name in ['maps-before.txt','maps-before-touch.txt','maps-after.txt']:
        p=root/name
        if p.exists():maps.extend(line for line in p.read_text().splitlines() if '/oat/arm64/toutiao.' in line)
    faults=[]
    for p in root.glob('cppcrash*'):
        text=p.read_text(errors='replace');header=text.split('Registers:',1)[0]
        faults.append(dict(file=p.name,header=header,
                           patch_update_malloc='Name:PatchUpdateMana' in header and '__libc_malloc_impl' in header and 'libshadowhook.so' in header))
    return dict(name=root.name,arm=r['arm'],protocol=r.get('protocol','preliminary'),outcome=r['outcome'],
                consent_uptime=consent,touch_uptime=touch,
                last_consent_to_touch_s=round(touch[0]-last[-1],3) if touch and last else None,
                consent_events=select(consent),article_events=select(touch),
                activity_times=activity_times,detail_lifecycle=lifecycle,detail_observations=r['detail_observations'],
                fatal_signals=fatal,faults=faults,parent_reap=[line for line in (root/'parent.log').read_text(errors='replace').splitlines() if '[WESTLAKE-REAP]' in line],app_image_loads=images,oat_maps=sorted(set(maps)),
                oat_diagnostics=rejects,measurement_error=r.get('error'),
                first_feed_heuristic_uptimes=stamps(r.get('first_feed_screenshot_uptimes')))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);args=ap.parse_args()
    rows=[analyze(p.parent) for p in sorted(args.root.glob('*/result.json')) if (p.parent/'child.stderr').exists()]
    print(json.dumps(rows,indent=2,ensure_ascii=False))
