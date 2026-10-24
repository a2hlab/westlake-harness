#!/usr/bin/env python3
"""Read existing T123 receipts only. Never calls a device or writes into a run."""
from pathlib import Path
import hashlib,json
RUN_NAME='run-20261024-110541-e2b1c729'
RUN=Path.home()/'.local/share/westlake/existing-demo-reentry-20261024'/RUN_NAME
OUT=Path(__file__).resolve().parent
load=lambda n:json.loads((RUN/n).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
clock=load('clock.json');click=load('click-once.json');reservation=load('single-click-reservation.json');owner=load('owner-result.json')
assert click['rc']==0 and not click['timeout']
images=[]
for name,receipt in [('initial.jpeg','p2-6.json'),('unlocked.jpeg','unlocked-image-recv.json')]+[(f's{x}.jpeg',f's{x}-recv.json') for x in (10,30,60,90,120)]:
    if not (RUN/receipt).exists():continue
    rec=load(receipt);assert rec['rc']==0 and not rec['timeout'] and (RUN/name).read_bytes()[:2]==b'\xff\xd8'
    images.append({'image':name,'sha256':sha(RUN/name),'recv_receipt':receipt,'received_wallclock':rec['end_wallclock'],'received_T_plus':rec['end_monotonic']-clock['monotonic']})
samples=[]
for offset in (10,30,60,90,120):
    filename=f's{offset}-identity.stdout'
    if not (RUN/filename).exists():continue
    rec=load(f's{offset}-identity.json');assert rec['rc']==0 and not rec['timeout']
    lines=(RUN/filename).read_text().splitlines();assert lines[0]==load('plan.json')['baseline_receipt']['boot']
    children=[]
    for number,line in enumerate(lines,1):
        fields=line.split(None,3)
        if len(fields)==4 and all(v.isdigit() for v in fields[:3]) and fields[3]=='com.ss.android.article.news':
            children.append({'pid':int(fields[0]),'ppid':int(fields[1]),'uid':int(fields[2]),'source_line':number})
    ready=load(f's{offset}-image-ready.json')
    samples.append({'nominal_seconds':offset,'actual_image_seconds_from_click_reservation':ready['offset_actual'],'children':children,'process_receipt':f's{offset}-identity.json','process_stdout':filename,'process_observation_start':rec['start_wallclock'],'process_observation_end':rec['end_wallclock']})
assert [x['nominal_seconds'] for x in samples]==[10,30,60,90]
assert [len(x['children']) for x in samples]==[0,0,1,1]
assert all(x['children'][0]['pid']==22035 for x in samples[2:])
held=load('cleanup-final-held.json');assert held['rc']==1 and (RUN/'cleanup-final-held.stdout').read_bytes()==b'' and (RUN/'cleanup-final-held.stderr').read_bytes()==b''
assert owner['cleanup']['restored'] and owner['cleanup']['lock_released'] and owner['cleanup']['power_after']=={'base':30000,'override':10000}
assert not owner['cleanup']['failure_home']['attempted'] and not (RUN/'failure-home-once.json').exists()
feed=load('feed-review-consumed.json');assert feed['review']['image']=='s60.jpeg' and feed['review']['image_sha256']==sha(RUN/'s60.jpeg')
for src,dst in [('unlocked.jpeg','host-white.jpeg'),('s60.jpeg','s60.jpeg'),('s90.jpeg','s90.jpeg')]:assert sha(RUN/src)==sha(OUT/'screenshots'/dst)
def build_facts(images,samples,commands,power,held):
    image_names=[Path(image['image']).stem for image in images]
    sample_names=[f"s{sample['nominal_seconds']}" for sample in samples if f"s{sample['nominal_seconds']}" in image_names]
    initial_names=[name for name in image_names if name in ('initial','unlocked')]
    successful=lambda label: int(commands.get(label) is not None and commands[label]['rc']==0 and not commands[label]['timeout'])
    child_counts=','.join(f"s{sample['nominal_seconds']}:{len(sample['children'])}" for sample in samples)
    child_samples='_'.join(f"s{sample['nominal_seconds']}" for sample in samples if sample['children'])
    child_pids=','.join(str(pid) for pid in sorted({child['pid'] for sample in samples for child in sample['children']}))
    return '\n'.join([
        'run='+RUN_NAME,
        f'screenshots_received={len(images)}',
        f"post_click_samples_received={len(sample_names)} ({','.join(sample_names)})",
        f"initial_images_received={len(initial_names)} ({','.join(initial_names)})",
        f"unlock_swipes={successful('unlock-once')}",
        f"desktop_home_before_click={successful('home')}",
        f"icon_clicks={successful('click-once')}",
        f"failure_home_after_click={successful('failure-home-once')}",
        'article_child_counts='+child_counts,
        f"article_child_pid_at_{child_samples or 'none'}={child_pids or 'none'}",
        f"power_restored=Timeout:{power['base']}ms,OverrideTimeout:{power['override']}ms",
        f"final_held=rc{held['rc']},stdout_empty,stderr_empty",
    ])+'\n'
commands={label:load(label+'.json') if (RUN/(label+'.json')).exists() else None for label in ('unlock-once','home','click-once','failure-home-once')}
facts=build_facts(images,samples,commands,owner['cleanup']['power_after'],held)
keys=['clock.json','context.json','manifest.json','p0-result.json','single-click-reservation.json','click-once.json','outer-review.json','review-consumed.json','feed-review.json','feed-review-consumed.json','failure-home-result.json','cleanup-power.stdout','cleanup-unlock.json','cleanup-final-held.json','cleanup-final-held.stdout','cleanup-final-held.stderr','owner-result.json','launcher-exit.json']
keys += [x['recv_receipt'] for x in images]+[x['image'] for x in images]
for sample in samples:keys += [sample['process_receipt'],sample['process_stdout']]
result={'status':'OBSERVED_EXISTING_VERSION_FEED_RECOVERY_NOT_SEAL','raw_run':'$HOME/.local/share/westlake/existing-demo-reentry-20261024/'+RUN_NAME,'manifest_sha256':sha(RUN/'manifest.json'),'facts':facts,'T0':clock,'click_dispatch':click['start_wallclock'],'click_dispatch_T_plus':click['start_monotonic']-clock['monotonic'],'click_reservation_to_dispatch_seconds':click['start_monotonic']-reservation['monotonic'],'images':images,'samples':samples,'outer_visual_findings':{'s60':'Multiple Chinese feed titles and bottom navigation; image placeholders (outer message and matching feed-review).','s90':'Recommendation images/video covers loaded; bottom navigation normal (outer user message).','video_playback':'not demonstrated'},'child_bound':'absent at s10/s30; PID22035 observed at s60/s90; creation time/birth not independently captured','feed_consumed_T_plus':feed['observed_monotonic']-clock['monotonic'],'s90_before_feed_receipt':'s90 was already captured before the s60 review was published; no s120 captured','cleanup':owner['cleanup'],'end_wallclock':owner['end_wallclock'],'elapsed_seconds':owner['elapsed'],'limitations':['Existing-version same-boot ordinary reopening only.','No runtime modifications, API freeze or seal claim.','Process sampling does not establish the exact spawn moment or precise latency cause.','No additional device operations after this owner finished.'],'source_sha256':{name:sha(RUN/name) for name in sorted(set(keys))}}
if __name__=='__main__':print(json.dumps(result,indent=2))
