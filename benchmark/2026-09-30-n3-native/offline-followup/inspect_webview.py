#!/usr/bin/env python3
"""Read exact deployed DEX only; no VM, board, or runtime mutation."""
import hashlib,json,sys,zipfile
from pathlib import Path
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
R=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths
P=Path(__file__).resolve().parent;W=lab_paths.workspaces()
inputs=[(W/'westlake-generation-n2-51a78bde/payload/android/framework/framework.jar',{'Landroid/webkit/WebViewFactory;':{'getProvider','isWebViewSupported'}}),
 (W/'westlake-generation-n2-51a78bde/payload/android/framework/oh-adapter-framework.jar',{'Ladapter/packagemanager/PackageManagerAdapter;':{'hasSystemFeature'}}),
 (W/'vm-copies/j3-75c2068c/oh-adapter-runtime.jar',{'Ladapter/packagemanager/PackageManagerAdapter;':{'hasSystemFeature'},'Ladapter/activity/PackageManagerProjectionProxy;':{'invoke'},'Ladapter/core/LocalServiceBinders;':set()})]
rows=[]
for path,classes in inputs:
 row={'input':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'methods':[]}
 with zipfile.ZipFile(path) as z:
  for name in z.namelist():
   if not name.endswith('.dex'):continue
   d=DEX(z.read(name))
   for cn,names in classes.items():
    c=d.get_class(cn)
    if not c:continue
    for m in c.get_methods():
     if names and m.get_name() not in names:continue
     ins=[{'offset':i,'opcode':x.get_name(),'operands':x.get_output()} for i,x in m.get_instructions_idx()]
     if not names and not any('webview' in x['operands'].lower() for x in ins):continue
     row['methods'].append({'class':cn,'method':m.get_name(),'descriptor':m.get_descriptor(),'instructions':ins})
 rows.append(row)
(P/'webview-dex.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row['sha256'][:8],[(m['class'],m['method']) for m in row['methods']])
