"""Local files only: preserve T29 four candidate files, replace only shim."""
import argparse,json,shutil
from pathlib import Path
from window_paths import final_data,sha,load

def main():
 p=argparse.ArgumentParser();p.add_argument('--t29-inputs',type=Path,required=True);p.add_argument('--production',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=final_data();params=load(d/'parameters.json');art=params['artifacts'];assert len(art)==6
 rows=[]
 for item in art[1:]:
  name=Path(item['path']).name;src=(a.production/'shim.so') if name=='libwebview_bionic_shim.so' else a.t29_inputs/name
  assert sha(src)==item['after_sha256'],name
  rows.append((src,name,item['after_sha256']))
 assert not a.out.exists();a.out.mkdir(parents=True)
 for src,name,h in rows:shutil.copyfile(src,a.out/name);assert sha(a.out/name)==h
 (a.out/'manifest.json').write_text(json.dumps({'status':'LOCAL_CANDIDATE_FILES_ONLY','device_calls':0,'files':[{'file':n,'sha256':h,'bytes':(a.out/n).stat().st_size} for _,n,h in rows]},indent=2)+'\n');print(a.out)
if __name__=='__main__':main()
