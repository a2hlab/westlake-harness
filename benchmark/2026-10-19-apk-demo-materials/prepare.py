import json, os, hashlib, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
WSP=Path(os.environ.get('WORKSPACES',REPO.parent))
MAIN=WSP/'westlake-harness'
ROUND=WSP/'westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/round'
OUT=HERE/'delivery'; (OUT/'originals').mkdir(parents=True,exist_ok=True)
E=HERE/'evidence'; E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resolved(s):return Path(s.replace('$WORKSPACES',str(WSP)).replace('$HOME',str(Path.home())))
def portable(p):return str(p).replace(str(WSP),'$WORKSPACES').replace(str(Path.home()),'$HOME')
source=MAIN/'benchmark/2026-10-14-final61b-full128-outer'
demo=read(source/'demo-list.json'); recommendations=read(MAIN/'benchmark/2026-10-14-final61b-full128-peer/startup-demo-recommendations.json')
meta={r['key']:r for r in read(ROUND/'batch-apps.json')['apps']}
excluded={r['key']:r for r in demo['excluded_keys_with_reasons']}
rows=[]
for a in recommendations['rows']:
 key=a['key']; m=meta[key]; p=resolved(a['actual_image']); assert sha(p)==a['actual_image_sha256'],key
 rp=resolved(a['record']); rec=read(rp); assert rec['key']==key
 image=OUT/'originals'/f'{key}{p.suffix}';shutil.copyfile(p,image)
 r=dict(key=key,name=m['name_zh'],category=m['category'],purpose=m['purpose_zh'],package=m['package'],scope='baseline128',status='excluded' if key in excluded else 'startup-only',reason=a['reason'],observed_limitations=a['observed_limitations'],exclusion_reason=excluded.get(key,{}).get('reason',''),image=str(image.relative_to(OUT)),image_sha256=sha(p),source_image=portable(p),source_record=portable(rp),source_record_sha256=sha(rp),date='2026-10-14',scheduled_seconds=a['scheduled_seconds'],raw_status=rec['status'],verified_scope='仅启动界面；未验证完整功能',width=Image.open(p).width,height=Image.open(p).height)
 rows.append(r)
boat_review=read(MAIN/'benchmark/2026-10-14-final61b-game-resume-review/review.json')
boat=next(x for x in boat_review['observations'] if x['tag']=='step-5-after');bp=MAIN/boat['path'];assert sha(bp)==boat['sha256']
tp=Path.home()/'.local/share/westlake/toutiao-resume-20261019/video-live-r1/before-video-tap/screen.jpeg'
for key,name,cat,purpose,p,scope,reason,date,package in [
 ('toutiao-route-b','今日头条','资讯与阅读','浏览新闻资讯与个性化信息流',tp,'信息流真实画面；历史专项含文章进入与返回','截图仅证明信息流呈现；不据此推断视频播放、新闻新鲜度或长期稳定性。','2026-10-19','com.ss.android.article.news'),
 ('boatattack','BoatAttack','3D 游戏','驾驶赛艇，在水上赛道转向与竞速',bp,'专项已验证转向、移动与复位','专项记录含 LAP 0→1；不代表完成一圈或整场比赛。系统状态栏遮挡部分 HUD。','2026-10-14','com.UnityTechnologies.BoatAttack')]:
  im=Image.open(p);dst=OUT/'originals'/f'{key}{p.suffix}';shutil.copyfile(p,dst)
  rows.append(dict(key=key,name=name,category=cat,purpose=purpose,package=package,scope='special-extra',status='scoped-special',reason=reason,observed_limitations=reason,exclusion_reason='',image=str(dst.relative_to(OUT)),image_sha256=sha(p),source_image=portable(p),source_record=portable(p.parent/'record.json'),date=date,scheduled_seconds=None,raw_status='separate-reviewed-evidence',verified_scope=scope,width=im.width,height=im.height))
# Ensure special package metadata agrees with recorded desktop inventory.
inv=read(MAIN/'benchmark/2026-10-14-demo-desktop-inventory/manifest.json')
for r in rows[-2:]:
 a=next(x for x in inv['apps'] if x['key']==r['key']);r['package']=a['package']
r=next(r for r in rows if r['key']=='cv2-com-nicue-onetwo')
r['purpose_original_metadata']=r['purpose'];r['purpose']='记录桌面游戏中的玩家生命值与分数。'
r['purpose_basis']='Visually inspected four-player life counter; narrowed from original broad metadata.'
assert len(rows)==130 and len({r['key'] for r in rows})==130
(OUT/'manifest.json').write_text(json.dumps(dict(baseline_keys=128,startup_only=115,excluded=13,special_extra=2,functional_all_usable=False,rows=rows),ensure_ascii=False,indent=2))
for src,name in [(source/'demo-list.json','source-demo-list.json'),(source/'results.json','source-results.json'),(MAIN/'benchmark/2026-10-14-final61b-game-resume-review/review.json','source-boat-review.json'),(ROUND/'facts.txt','facts.txt')]:shutil.copyfile(src,E/name)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
for page in range(0,len(rows),24):
 chunk=rows[page:page+24]; sheet=Image.new('RGB',(1440,1440),'#e9edf3');draw=ImageDraw.Draw(sheet)
 for i,r in enumerate(chunk):
  x=(i%6)*240;y=(i//6)*360
  im=Image.open(OUT/r['image']);im.thumbnail((226,300));sheet.paste(im,(x+(240-im.width)//2,y+28));draw.text((x+5,y+5),str(page+i+1)+' '+r['key'].removeprefix('cv2-')[:20],font=font,fill='black')
 sheet.save(E/f'contact-{page//24+1:02}.jpg')
print('Prepared',len(rows),'rows; 128 exact source hashes; originals copied')
