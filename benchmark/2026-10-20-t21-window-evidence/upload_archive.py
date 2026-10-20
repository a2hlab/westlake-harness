#!/usr/bin/env python3
"""Execute the prepared three archive argv; preserve original pending receipt."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 if not a.execute:print('Preview only: three prepared transfer argv, no build/device commands.');return
 src=HERE/'.private/archive-01';commands=json.loads((src/'remote-commands.private.json').read_text());expected=json.loads((src/'receipt.json').read_text());out=HERE/'.private/upload-01';out.mkdir(exist_ok=False)
 receipt={'status':'UPLOAD_STARTED','archive_sha256':expected['archive_sha256'],'bytes':expected['bytes'],'remote_verified':False,'commands':[]}
 def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 save()
 for i,cmd in enumerate(commands):
  assert cmd[0] in ['ssh','scp'];stem=str(i);(out/(stem+'.argv.json')).write_text(json.dumps(cmd,indent=2)+'\n');start=time.time()
  with (out/(stem+'.stdout')).open('wb') as so,(out/(stem+'.stderr')).open('wb') as se:
   try:rc=subprocess.run(cmd,stdout=so,stderr=se,timeout=300).returncode
   except subprocess.TimeoutExpired:rc=124
   except OSError as e:se.write(str(e).encode());rc=127
  (out/(stem+'.rc')).write_text(str(rc)+'\n');receipt['commands'].append({'index':i,'rc':rc,'seconds':time.time()-start,'files':[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.glob(stem+'.*'))]});save()
  if rc:receipt['status']='STOPPED_AT_FIRST_ERROR';save();print(json.dumps(receipt));return rc
 lines=(out/'2.stdout').read_text().splitlines();assert lines[0].split()[0]==expected['archive_sha256'] and int(lines[1])==expected['bytes'];receipt['remote_verified']=True;receipt['status']='REMOTE_VERIFIED';save();print(json.dumps(receipt));return 0
if __name__=='__main__':raise SystemExit(main())
