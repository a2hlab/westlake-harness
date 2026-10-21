#!/usr/bin/env python3
"""Extract bounded technical evidence from existing LLVM/DEX dump; no target execution."""
from pathlib import Path
import re,json,hashlib,mmap,argparse
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--raw-root',type=Path,required=True);a=ap.parse_args();raw=a.raw_root/'scan/raw';out=[]
for name,patterns in {'classes3':['com.combosdk.openapi.ComboApplication.attachBaseContext:','com.combosdk.openapi.ComboApplication.onCreate:','com.miHoYo.GetMobileInfo.MainActivity.onCreate:','org.fmod.FMODAudioDevice.run:'],'classes4':['com.unity3d.player.UnityPlayerActivity.onCreate:','com.mihoyo.combosdk.ComboSDKActivity.onCreate:','com.unity3d.player.UnityPlayer.<clinit>:','com.unity3d.player.UnityPlayer.loadLibraryStatic:','com.unity3d.player.UnityPlayer.a:(Landroid/content/pm/ApplicationInfo;)V']}.items():
 lines=(raw/(name+'.stdout')).read_text(errors='replace').splitlines()
 for pat in patterns:
  hits=[i for i,l in enumerate(lines) if '|[' in l and pat in l]
  for i in hits:
   j=i+1
   while j<len(lines) and not re.match(r'\s+catches\s+:',lines[j]):j+=1
   dest=a.raw_root/'selected'/f'{name}-{i+1}.txt';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('\n'.join(f'{k+1}: {lines[k]}' for k in range(i,j))+'\n')
   out.append({'method':pat,'dex':name+'.dex','raw':'scan/raw/'+name+'.stdout','start_line':i+1,'end_line':j,'selected_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'instructions':[{'line':k+1,'text':lines[k].strip()} for k in range(i,j) if re.search(r'(invoke-|const-string|if-|goto|throw|return)',lines[k])]})
(p/'startup-excerpts.json').write_text(json.dumps(out,indent=2)+'\n')
lib=a.raw_root/'scan/members/lib/arm64-v8a/libyuanshen.so';hits=[]
with lib.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
 for pattern in [rb'20[0-9]{2}\.[0-9]+\.[0-9]+[abfp][0-9]+',rb'lib(?:unity|il2cpp|vulkan|OpenSLES|aaudio)[^\x00\s]{0,35}',rb'AAudio[A-Za-z_0-9]{1,80}',rb'AudioTrack',rb'UnityPlayer',rb'global-metadata.dat',rb'il2cpp_init',rb'SL_IID_[A-Z_]{1,60}',rb'FMOD [^\x00\r\n]{0,50}']:
  matches=[];total=0
  for q in re.finditer(pattern,m):
   total+=1
   if len(matches)<80:matches.append({'file_offset':hex(q.start()),'text':q[0].decode(errors='replace')})
  hits.append({'pattern':pattern.decode(),'matches':matches,'total_matches':total,'limit_per_pattern':80,'status':'STRING_REFERENCE_NOT_CALL_OR_VERSION_PROOF'})
(p/'native-string-hints.json').write_text(json.dumps({'member':'lib/arm64-v8a/libyuanshen.so','sha256':'3dd8a20da6c1f11b966ae2b260cf1dd09b6667609f435a5b1bc05887c46b2a29','hints':hits},indent=2)+'\n')
print(json.dumps({'selected_methods':len(out),'string_hints':[(x['pattern'],x['total_matches']) for x in hits]}))
