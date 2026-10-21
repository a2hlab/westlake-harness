from pathlib import Path
import hashlib,json,sys
w=Path(sys.argv[1])
terms=['zigzag-final-r155','zigzag-r138h-sealed-generation-source','zigzag-r148-source','zigzag-r150-sealed-generation-thin.bundle','post-rollback-redeploy/identities.txt','libsigchain','libunwindstack','real-work']
result=[]
for dirname in ['_airdrop-20260930-delta','_airdrop-20260930-delta2']:
 for filename in ['delta.tar.zst.files','octos-state.tar.zst.files']:
  p=w/dirname/filename
  data=p.read_bytes()
  separator=b'\0' if b'\0' in data else b'\n'
  rows=[x.decode('utf-8') for x in data.split(separator) if x]
  result.append({'path':dirname+'/'+filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'separator':'NUL' if separator==b'\0' else 'LF','members':len(rows),'matches':{term:[r for r in rows if term in r] for term in terms}})
print(json.dumps(result,indent=2))
