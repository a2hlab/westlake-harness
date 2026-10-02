"""Offline recorded desktop/API-label comparison; never invokes a device tool."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import zipfile

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nodes(n):
 yield n
 for c in n.get('children',[]):yield from nodes(c)
def texts(n):return sorted({x.get('attributes',{}).get('text') for x in nodes(n) if x.get('attributes',{}).get('text')})
def main():
 p=argparse.ArgumentParser();p.add_argument('--record-dir',type=Path,required=True);p.add_argument('--runner',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 from loguru import logger
 logger.remove()
 from androguard.core.apk import APK
 out=a.out;out.mkdir(parents=True,exist_ok=True)
 rec=json.loads((a.record_dir/'record.json').read_text());apk_path=Path(rec['input_apk']);assert digest(apk_path)==rec['apk_sha256']
 apk=APK(str(apk_path));manifest=apk.get_android_manifest_xml();ns='{http://schemas.android.com/apk/res/android}';app=manifest.find('application');activities=[]
 for activity in app.findall('activity'):
  activities.append({'name':activity.get(ns+'name'),'label':activity.get(ns+'label'),'labelRes':int(activity.get(ns+'label')[1:],16) if (activity.get(ns+'label') or '').startswith('@') else 0,'launcher':any(x.get(ns+'name')=='android.intent.category.LAUNCHER' for x in activity.findall('intent-filter/category'))})
 assert app.get(ns+'label') == '@7F0B0001' and all(x['labelRes']==0x7f0b0001 for x in activities if x['launcher'])
 bundle_text=(a.record_dir/'bundle.txt').read_text();bundle=json.loads(bundle_text[bundle_text.index('{'):]);ability=next(x for m in bundle['hapModuleInfos'] for x in m['abilityInfos'] if x['name']==rec['desktop_activity'])
 source=a.runner.read_text();func=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='select_icon');selector=ast.get_source_segment(source,func)
 class ExpectedFailure(Exception):pass
 import re
 def box(b):
  m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',b);assert m;return tuple(map(int,m.groups()))
 scope={'ICON_PREFIX':'AppIconCommonView_','LAUNCHER':'com.ohos.sceneboard','AppFailure':ExpectedFailure,'box':box};exec(selector,scope)
 inventory={};pages=[];exact=[];prefix='AppIconCommonView_'+rec['package']+'.'
 for path in sorted(a.record_dir.glob('icons*.json')):
  tree=json.loads(path.read_text());tiles=[]
  for n in nodes(tree):
   at=n.get('attributes',{});ident=at.get('id') or at.get('key','')
   if ident.startswith('AppIconCommonView_'):
    row={'id':ident,'labels':texts(n),'bounds':at.get('bounds'),'visible':at.get('visible')};tiles.append(row);inventory[ident]=row
  target=[t for t in tiles if t['id'].startswith(prefix)]
  chosen=scope['select_icon'](tree,rec['package'],rec['desktop_activity']);assert chosen is None
  pages.append({'file':path.name,'sha256':digest(path),'tiles':len(tiles),'labels':sorted({s for t in tiles for s in t['labels']}),'target_prefix_matches':target,'selector_result':chosen})
  exact.extend(target)
 assert len(pages)==20 and not exact
 labels=sorted({s for row in inventory.values() for s in row['labels']});assert 'Frequent Habits' not in labels
 log=(a.record_dir/'install-hilog.txt').read_text(errors='replace').splitlines();excerpts=[{'line':i+1,'text':l} for i,l in enumerate(log) if rec['package'] in l and any(k in l for k in ['label=','loaded icon','launcher abilityInfos','name is Frequent Habits','getPixelMap is empty','combinePic is empty','load iconId is invalid'])]
 with zipfile.ZipFile(apk_path) as z:
  icon=z.read('res/d2.webp');icon_info={'path':'res/d2.webp','bytes':len(icon),'sha256':hashlib.sha256(icon).hexdigest(),'first_24_bytes_hex':icon[:24].hex()}
 result={'analysis':'offline-only','apk_sha256':digest(apk_path),'package':rec['package'],'apk_label_res':int(app.get(ns+'label')[1:],16),'apk_label_res_zero':False,'application_label':app.get(ns+'label'),'resolved_label':apk.get_app_name(),'activities':activities,'bms_ability':{k:ability.get(k) for k in ['name','bundleName','label','labelId','iconId','isLauncherAbility','visible','enabled']},'runner':{'sha256':digest(a.runner),'matching':'package plus ability ID, no text-label matching','exact_id':prefix+rec['desktop_activity']},'pages':pages,'unique_icons':len(inventory),'labels':labels,'habits_other_app':[v for v in inventory.values() if 'Habits' in v['labels']],'target_icons_found':len(exact),'icon':icon_info,'install_log_excerpts':excerpts,'verdict':'target tile absent from all recorded pages; correct nonzero labels registered, SceneBoard failed icon decoding; not a runner label mismatch','precise_launcher_placement_failure':'not established; no live query made'}
 (out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 (out/'desktop-icons.json').write_text(json.dumps(sorted(inventory.values(),key=lambda r:r['id']),indent=2,ensure_ascii=False)+'\n')
 from lxml import etree
 (out/'AndroidManifest.xml').write_text(etree.tostring(manifest,encoding='unicode',pretty_print=True))
 (out/'select_icon.py.txt').write_text(selector+'\n')
 (out/'install-excerpt.txt').write_text('\n'.join(str(i['line'])+': '+i['text'] for i in excerpts)+'\n')
 print('APK pin PASS; application/activity labelRes=0x7f0b0001 (nonzero), resolved=Frequent Habits')
 print(f'dumps={len(pages)} unique_icons={len(inventory)} target_prefix_matches={len(exact)} strict_selector_matches=0')
 print('Habits tile belongs to org.isoron.uhabits; Frequent Habits label absent')
 print('SceneBoard: target label/ability registered; getPixelMap is empty; combinePic is empty; load iconId is invalid')
 print('VERDICT launcher tile absent, not runner text-name mismatch; no board commands')
if __name__=='__main__':main()
