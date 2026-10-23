from pathlib import Path
import json,zipfile,hashlib,struct
out=Path(__file__).resolve().parent
main=out.parents[2]/'westlake-harness'
home=Path.home()/'.local/share/westlake'
hap=home/'toutiao-launcher-20261020/release-01/candidate-signed.hap'
raw=home/'spare-board-icon-observation-20261023/raw'
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p).replace(str(Path.home()),'$HOME'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
assert sha(hap.read_bytes())=='b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
t89=main/'benchmark/2026-10-23-host-lifecycle-latency/results.json'
binding=json.loads(t89.read_text())['binding']
source=main/'benchmark/2026-10-20-toutiao-launcher-page/sources/baseline/EntryAbility.js'
assert sha(source.read_bytes())==binding['actual_entry_source_sha256']
with zipfile.ZipFile(hap) as z:
 m=json.loads(z.read('module.json'));a=m['module']['abilities'][0]
 assert sha(z.read('ets/entryability/EntryAbility.abc'))==binding['entry_abc_sha256']
 idx=z.read('resources.index');pos=idx.index(b'IDSS');count=struct.unpack_from('<I',idx,pos+4)[0];resources=[]
 for n in range(count):
  rid,offset=struct.unpack_from('<II',idx,pos+8+n*8)
  size,typ,recordid=struct.unpack_from('<III',idx,offset);assert rid==recordid
  vl=struct.unpack_from('<H',idx,offset+12)[0];value=idx[offset+14:offset+14+vl].rstrip(b'\0').decode()
  no=offset+14+vl;nl=struct.unpack_from('<H',idx,no)[0];name=idx[no+2:no+2+nl].rstrip(b'\0').decode()
  resources.append({'id':rid,'id_hex':hex(rid),'record_offset':offset,'type':typ,'name':name,'value':value})
 assert next(x['value'] for x in resources if x['id']==a['labelId'])=='今日头条'
 members={n:{'sha256':sha(z.read(n)),'bytes':len(z.read(n))} for n in ['module.json','ResourceTable.txt','resources.index','resources/base/media/app_icon.png','resources/base/media/icon.png','ets/entryability/EntryAbility.abc','resources/base/profile/main_pages.json']}
 (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 (out/'resource-map.json').write_text(json.dumps(resources,ensure_ascii=False,indent=2)+'\n')
 layouts=[]
 def walk(node):
  if isinstance(node,dict):
   yield node.get('attributes',{})
   for child in node.get('children',[]):yield from walk(child)
 for i in range(5):
  p=raw/'01'/f'l{i}.json';nodes=list(walk(json.loads(p.read_text())))
  ids={a.get('id','') for a in nodes};workspaces=sorted(x for x in ids if x.startswith('SwiperPage_Grid_WorkSpace_'));icons=sorted(x for x in ids if x.startswith('AppIconCommonView_'))
  matches=[{'id':n.get('id'),'text':n.get('text'),'bundleName':n.get('bundleName'),'abilityName':n.get('abilityName')} for n in nodes if any(s in str(n.get(k,'')) for s in ['org.westlake.imehost','今日头条','com.ss.android.article.news'] for k in ['id','key','text','bundleName','abilityName','description'])]
  layouts.append({'file':f'raw/01/l{i}.json','pin':pin(p),'workspace_ids':workspaces,'unique_icon_ids':len(icons),'screen_lock':'ScreenLockRootComponent' in ids,'target_matches':matches,'location':'single-line JSON; attributes.id / attributes.text, recursively through children'})
 receipts={}
 for n in ['bm','bm2','home','pg','pg2']:
  receipts[n]={'argv':json.loads((raw/'01'/f'{n}.argv').read_text()),'rc':(raw/'01'/f'{n}.rc').read_text().strip(),'stdout':(raw/'01'/f'{n}.stdout').read_text(),'pins':{ext:pin(raw/'01'/f'{n}.{ext}') for ext in ['argv','rc','stdout','stderr']}}
  receipts[n]['argv'][0]='<installed hdc path; receipt pin retained>'
 result={'task':'T105','status':'identity_bound_no_manifest_candidate','hap':pin(hap),'historical_binding':{'t89_results':pin(t89),'entry_source':pin(source),'entry_abc_sha256':binding['entry_abc_sha256'],'scope':'Reuse T89 historical binding, no timing reanalysis'},'identity':{'bundle':m['app']['bundleName'],'module':m['module']['name'],'ability':a['name'],'mainElement':m['module']['mainElement'],'label':'今日头条','label_reference':a['label'],'label_id':a['labelId'],'skills':a['skills'],'exported':a['exported'],'visible':a['visible'],'app_icon_reference':m['app']['icon'],'ability_icon_reference':a['icon'],'app_icon_member':'resources/base/media/app_icon.png','ability_icon_member':'resources/base/media/icon.png'},'members':members,'layouts':layouts,'coverage':{'distinct_workspace_pages':[0,1,2],'desktop_samples':4,'lock_samples':1,'complete_desktop_coverage':False,'target_matches_in_supplied_layouts':0},'t103_receipts':receipts,'limits':['T103 bm2 confirms bundle-list occurrence only; no installed-HAP SHA or resolved installed label/ability is supplied here.','The T89 SHA-pinned HAP identity is not a fresh installed-artifact binding for the T103 spare board.','Only workspace pages 0,1,2 are covered; no global absent-icon claim.','Suggested AppIconCommonView_org.westlake.imehost.EntryAbility is inferred from observed launcher ID pattern, not observed target node.','CC must confirm live node identity and bounds from new layout; no old coordinates supplied.'],'cc_locator':{'bundle':'org.westlake.imehost','ability':'EntryAbility','label':'今日头条','inferred_icon_id':'AppIconCommonView_org.westlake.imehost.EntryAbility','bounds':'unknown; obtain from new CC layout'},'candidate':None,'reason':'Expected launcher declaration and referenced resources exist; supplied finite layouts do not establish a manifest defect.','device_calls':0,'rea_calls':0}
 (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PASS: HAP/source/ABC pins, resource ID-to-label mapping, five raw layouts independently parsed; no manifest candidate.')
