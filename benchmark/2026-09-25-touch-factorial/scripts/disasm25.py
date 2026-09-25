import zipfile,pathlib
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
apk=pathlib.Path.home()/'a2hlab/app-inputs/toutiao/toutiao.apk'
out=pathlib.Path.home()/'a2hlab/board/5ea34a4500000000000000001123012c/touch25/disasm-upload.txt'
targets={'LX/Ja1;','Lcom/bytedance/news/ug_daoliang/content/ContentSituationServiceImpl;','Lcom/bytedance/news/ug_daoliang/saasImpl/SassAppListUploadInitTask;'}
with out.open('w') as f,zipfile.ZipFile(apk) as z:
 for name in z.namelist():
  if not name.endswith('.dex'):continue
  raw=z.read(name)
  if not any(t.encode() in raw for t in targets):continue
  dex=DEX(raw)
  for c in dex.get_classes():
   if c.get_name() not in targets:continue
   print('FOUND',name,c.get_name(),flush=True)
   f.write('\nDEX '+name+' CLASS '+c.get_name()+' SUPER '+c.get_superclassname()+'\n')
   for m in c.get_methods():
    f.write('\nMETHOD '+m.get_name()+' '+m.get_descriptor()+'\n')
    for off,ins in m.get_instructions_idx():f.write(f'{off:04x} {ins.get_name()} {ins.get_output()}\n')
