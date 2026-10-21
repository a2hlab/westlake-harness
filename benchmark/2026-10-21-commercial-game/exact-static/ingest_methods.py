#!/usr/bin/env python3
"""Bind five outer-executed REA method records; preserve originals privately."""
import argparse,json,hashlib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2)+'\n')
def record(d):
 if isinstance(d,dict) and 'evidence_id' in d and 'subject' in d:return d
 if isinstance(d,dict) and isinstance(d.get('structuredContent'),dict):return record(d['structuredContent'])
 if isinstance(d,dict):
  for c in d.get('content',[]):
   if c.get('type')=='text':
    try:return record(json.loads(c['text']))
    except (ValueError,KeyError):pass
 raise ValueError('no complete structured Evidence')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true',required=True);ap.add_argument('--outer',type=Path,required=True);a=ap.parse_args()
 classes=['com.combosdk.openapi.ComboApplication']*2+['com.miHoYo.GetMobileInfo.MainActivity','com.unity3d.player.UnityPlayer','org.fmod.FMODAudioDevice']
 methods=['attachBaseContext','onCreate','onCreate','loadLibraryStatic','run']
 needles=[['isRedirect(4)','super.attachBaseContext','invocationDispatch'],['isRedirect(5)','CryptoUtils.init','Initializer.INSTANCE.start','super.onCreate','setDataDirectorySuffix'],['super.onCreate','layoutInDisplayCutoutMode','mihoyo : onCreate'],['System.loadLibrary','return true','catch (Exception','catch (UnsatisfiedLinkError','Unable to find','return false'],['int i2 = 3','getMinBufferSize','new AudioTrack','getState() == 1','allocateDirect','AudioTrack failed','i2 += -1','fmodProcess','this.c.write']]
 findings=[
  'Default attachBaseContext delegates to superclass; RuntimeDirector may replace it. Static branch condition is known; runtime director value is not.',
  'Default onCreate sets context, initializes CryptoUtils then Initializer before Application.onCreate. Redirect(5) returns early. Only WebView suffix handling has the shown local Exception catch; do not infer startup calls are swallowed.',
  'MainActivity calls super.onCreate before cutout configuration and the mihoyo marker. Absence of that marker alone does not identify a failing library or renderer.',
  'System.loadLibrary success returns true. Exception and UnsatisfiedLinkError are logged at Unity level 6 and return false. The latter message discards the linker exception detail; the clinit fallback to main is not proof that loading succeeded. Native linker stderr is needed for the concrete failure.',
  'FMOD uses max(round(minBuffer*1.1)&~3, fmodInfo(j)*fmodInfo(i)*4), a six-int AudioTrack constructor, getState()==1, and native fmodProcess before byte-array write. Failed initialization releases and decrements an initial three-attempt budget; success resets it. This method ignores fmodProcess/write return values. No claim of selected backend, audible output, or effective-ring getter coverage.'
 ]
 rows=[]
 for i in range(5):
  src=a.outer/f'method-{i}.tool-result.json';d=record(json.loads(src.read_text()));n=d['normalized_result']
  assert d['subject']['digest']['sha256']==EXPECTED and d['operation']=='inspect_android_method'
  assert d['parameters']['class_name']==classes[i] and d['parameters']['method_name']==methods[i]
  assert n['body_status']=='available' and n['source']['status']=='complete' and not n['fell_back']
  dst=D/'.private/g04-01/outer-rea'/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  lines=n['source']['text'].splitlines();selected=[]
  for needle in needles[i]:
   hits=[j+1 for j,s in enumerate(lines) if needle in s];assert hits,(i,needle)
   selected.append({'anchor':needle,'source_lines':hits})
  rows.append({'method':classes[i]+'.'+methods[i],'method_metadata':n['method'],'evidence_id':d['evidence_id'],'artifact_sha256':EXPECTED,'executed_by':'outer(codex)','analyzed_by':'inner(codex)','provider':d['provider'],'engine':n['engine'],'body_status':n['body_status'],'source_status':n['source']['status'],'source_sha256':hashlib.sha256(n['source']['text'].encode()).hexdigest(),'source_line_count':len(lines),'raw':{'alias':'$G04_PRIVATE/outer-rea/'+src.name,'sha256':sha(src),'bytes':src.stat().st_size},'anchors':selected,'finding':findings[i],'limitations':d['limitations']})
 put(D/'rea-method-findings.json',{'status':'FIVE_EXACT_METHODS_CONSUMED','records':rows,'runtime':'NOT_TESTED'})
 ledger=json.loads((D/'rea-ledger.json').read_text());ledger['method_requests_pending']=[];ledger['successful_methods']=[{k:r[k] for k in ['method','evidence_id','artifact_sha256','executed_by','raw']} for r in rows];ledger['status']='STATIC_METHOD_ANALYSIS_COMPLETE';put(D/'rea-ledger.json',ledger)
 r=json.loads((D/'results.json').read_text());r['status']='STATIC_ANALYSIS_COMPLETE_RUNTIME_NOT_TESTED';r['rea_methods_consumed']=5;put(D/'results.json',r)
 m=json.loads((D/'startup-matrix.json').read_text())
 for x in m['rows']:
  if x['id'] in ['application','launcher','native-load','fmod-audio']:x['additional_evidence']='rea-method-findings.json'
 put(D/'startup-matrix.json',m)
 print(json.dumps({'status':'PASS','methods':5,'artifact_sha256':EXPECTED,'executed_by':'outer(codex)'}))
if __name__=='__main__':main()
