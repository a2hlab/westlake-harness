from pathlib import Path
import json,hashlib,shutil,tempfile,subprocess,csv,io
R=Path.cwd();M=R.parent/'westlake-harness';B=Path('benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-live-review');P=R/B;A=Path('benchmark/2026-10-19-api-progress-update');out=R/A
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def w(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def ref(s):
 p=R/s if s.startswith(str(B)) else M/s
 assert p.is_file() and not p.is_symlink(),s
 return {'path':s,'sha256':h(p)}
old=json.loads((M/A/'observations.json').read_text());new=json.loads(json.dumps(old));assert len(old['rows'])==3
v='benchmark/2026-10-19-toutiao-video-playback/'
row={'id':'OBS-20261019-PLAYER-R4','kind':'精确二进制派生候选 / 播放器集成观察（公共API未冻结）','name':'TTPlayer cache槽自绑定与OpenSL IID对象级观察','status':'三个GOT槽匹配；视频未通过；候选已回滚','method':'沿用run79275cf9、compat9f558aaf、media d2882303，新增player b427614d→5fba8050固定派生件（105槽、627字节差异）；实读两个OpenSL IID槽和一个原fault相关player cache槽，三者匹配预期地址。','platform':'61b / arm64；候选boot fade993a，恢复boot eef63e15；APK a1112a0c。本条未新增独立平台版本采样。','apps':'今日头条1个APK。视频tab、中心点击、上滑换封面三组各t5/t20/t25实际图；封面内容未见动态。末组换到另一封面，同组仍静止。','limitations':'仅三槽对象绑定有实读，不证明全部105槽执行、完整加载、解码、Surface或声音语义。原三份got.json仍unknown，后续独立读数另列。三组25秒不是契约两轮有声播放；标准alive表unknown，PID/birth前后样本不等于连续存活。leave-video仍视频，home-feed为空评论框，均非返回feed。','deployment':'四件按原apply-plan回滚：run d3518cef/media fecf91e1/player b427614d恢复，compat文件及父映射absent，P0 cfg91e31b95保留。freshboot eef63e15 parent5826/8498 child8384/10007真实feed ccc500ec；MAIN20:28:45解锁，同plan62targets/351labels/config无差。','source':[ref(v+'candidate-r4/derive_ttmplayer_selfrel.py'),ref(v+'candidate-r3/derive_mffmpeg.py'),ref(v+'candidate/src/opensles_android_compat.c')],'build':[ref(v+'candidate/build_candidate.sh'),ref(v+'candidate/toolchain-manifest.json'),ref(str(B/'archive/build-artifacts-receipt.json')),ref(str(B/'archive/static-build-review.json'))],'evidence':[ref(str(B/x)) for x in ['README.md','results.json','got-read-r2/result.json','got-read-r2/independent-check.json','got-read-r2/compat-load-bias.json','play1/t25.jpeg','center-tap/t25.jpeg','swipe-next/t25.jpeg','rollback-final/screen.jpeg','rollback-final/identity.txt','rollback-final/canonical-unlock.txt','archive/window-archive.json']],'frozen':False}
new['rows'].append(row);new['as_of']='2026-10-19T20:28:45+08:00'
# Use original renderer unchanged in isolated filesystem; no MAIN writes or simulated API semantics.
with tempfile.TemporaryDirectory(prefix='t4-r4-api-render-') as tmp:
 root=Path(tmp);dest=root/A;dest.mkdir(parents=True)
 shutil.copyfile(M/A/'render.py',dest/'render.py');w(dest/'observations.json',new)
 for rr in new['rows']:
  for g in ['source','build','evidence']:
   for it in rr[g]:
    rel=it['path'];f=R/rel if rel.startswith(str(B)) else M/rel;assert h(f)==it['sha256'];t=root/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t)
 proc=subprocess.run(['python3',str(dest/'render.py')],capture_output=True,text=True)
 assert proc.returncode==0,proc.stderr
 out.mkdir(parents=True,exist_ok=True)
 for n in ['observations.json','observations.csv','index.html','results.json']:shutil.copyfile(dest/n,out/n)
 csvrows=list(csv.DictReader(io.StringIO((out/'observations.csv').read_text(encoding='utf-8-sig'))));assert len(csvrows)==4
 for x,y in zip(csvrows,new['rows']):
  for k in ['source','build','evidence']:assert json.loads(x[k])==y[k]
 assert new['rows'][:3]==old['rows']
 Q=R/'benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-api-final'
 Q.mkdir(exist_ok=True);(Q/'renderer.stdout.txt').write_text(proc.stdout);(Q/'renderer.stderr.txt').write_text(proc.stderr)
 check={'token':'video-1919-r4-final-packet','status':'API_ADDITIVE_RENDER_ACCEPT','renderer_source':str(A/'render.py'),'renderer_sha256':h(M/A/'render.py'),'renderer_unchanged':True,'renderer_rc':proc.returncode,'rows':4,'references_by_row':{rr['id']:sum(len(rr[g]) for g in ['source','build','evidence']) for rr in new['rows']},'references_total':sum(len(rr[g]) for rr in new['rows'] for g in ['source','build','evidence']),'first_three_rows_deep_equal':True,'historical315_modified':False,'main_input_sha256':h(M/A/'observations.json'),'output_sha256':h(out/'observations.json'),'device_calls':0,'builds_executed':0,'consumer_check':'Unmodified MAIN renderer executed against exact copied reference bytes in an isolated temporary root. All path/SHA assertions passed; output CSV reference fields checked.'}
 w(Q/'results.json',check)
 (Q/'ACK.md').write_text('# video-1919-r4-final-packet — API fourth observation\n\nACCEPT additive evidence only. First three row objects unchanged; historical315 untouched. Source, build receipts and live evidence are separate. Playback remains not passed; successful rollback does not upgrade capability. Unmodified MAIN renderer returned rc0; exact reference bytes validated in isolated root.\n')
 print(json.dumps(check,indent=2,ensure_ascii=False))
