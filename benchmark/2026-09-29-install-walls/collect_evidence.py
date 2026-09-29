#!/usr/bin/env python3
"""Snapshot small, numbered source/log excerpts. All input reads are local."""
from pathlib import Path
import json,subprocess,hashlib
from prepare import HERE,ROOT,OH,REL,sha
PKG=Path('bms/src/adapter/framework/package-manager/jni')
PATCH=Path('bms/src/adapter/ohos_patches')/REL
LEG=Path('/Users/zhaoyue/orca/westlake/westlake-deploy-ohos/v3-hbc')
REAL=Path('/Users/zhaoyue/orca/workspaces/01.OH61AOSP16/real-work')
LOG=ROOT/'benchmark/2026-09-28-bms-label-resolve/evidence/b3-onboard'
requests=[
 ('producer-bound',ROOT/PKG/'oh_adapter_install_apk_c_entry.cpp',411,418),
 ('manifest-error-enum',ROOT/PKG/'apk_verified_session_c_api.h',34,45),
 ('old-caller',OH/REL/'base_bundle_installer.cpp',1502,1522),
 ('repository-capacity',ROOT/PATCH/'base_bundle_installer.cpp.patch',45,67),
 ('real-work-capacity',REAL/'src/adapter/ohos_patches'/REL/'base_bundle_installer.cpp.patch',45,67),
 ('native-selection',ROOT/PKG/'native_payload_inspector.h',96,113),
 ('native-extractor',ROOT/PATCH/'installd/installd_operator.cpp.patch',85,244),
 ('real-work-elf-policy',REAL/'src/adapter/ohos_patches'/REL/'installd/installd_operator.cpp.patch',132,176),
 ('native-error-mapping',OH/REL/'installd/installd_host_impl.cpp',164,183),
 ('native-error-enum',OH/'foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include/appexecfwk_errors.h',217,227),
 ('old-workspace-extractor',Path('/Users/zhaoyue/orca/00.Workspace/src/adapter/framework/package-manager/jni/apk_installer.cpp'),876,941),
 ('westlake-extractor',LEG/'adapter-src/framework/package-manager/jni/apk_installer.cpp',440,505),
 ('westlake-old-capacity',LEG/'patches/ohos_patches/bundle_framework/services/bundlemgr/apply_bms_apk_register_with_manifest.py',118,130),
 ('toutiao-provisioning',ROOT/'benchmark/2026-09-27-device-provisioning/provision_toutiao.sh',40,65),
 ('x-prior-route',ROOT/'benchmark/2026-09-27-x-twitter-bringup/README.md',1,29),
 ('x-overflow',LOG/'x-hilog.txt',1564,1565),
 ('toutiao-overflow',LOG/'toutiao-hilog.txt',909,910),
 ('seal-manifest-fit',LOG/'fd-seal-hilog.txt',351,351),
 ('seal-native-prefix',LOG/'fd-seal-hilog.txt',409,416),
 ('seal-first-native',LOG/'fd-seal-hilog.txt',394,394),
 ('artifact-names',ROOT/'bms/src/adapter/build/config.sh',70,96),
 ('gn-native-target',OH/'foundation/bundlemanager/bundle_framework/services/bundlemgr/BUILD.gn',587,610),
 ('gn-sources',OH/'foundation/bundlemanager/bundle_framework/services/bundlemgr/appexecfwk_bundlemgr.gni',15,48),
]
rows=[];text=[]
for ident,p,start,end in requests:
 lines=p.read_text().splitlines()
 assert len(lines)>=end,(p,len(lines),end)
 header=f'[{ident}] {p}:{start}-{end} sha256={sha(p)}'
 first=len(text)+1;text.append(header)
 text.extend(f'{n}: {lines[n-1]}' for n in range(start,end+1));text.append('')
 rows.append({'id':ident,'path':str(p),'start':start,'end':end,'sha256':sha(p),'excerpt_line':first})
(HERE/'evidence/source-excerpts.txt').write_text('\n'.join(text)+'\n')
(HERE/'evidence/sources.json').write_text(json.dumps(rows,indent=2)+'\n')
versions=[]
for p in [ROOT,REAL,Path('/Users/zhaoyue/orca/00.Workspace'),LEG]:
 q=subprocess.run(['git','-C',str(p),'rev-parse','--show-toplevel','HEAD'],capture_output=True,text=True)
 versions.append({'path':str(p),'git':q.stdout.splitlines() if q.returncode==0 else 'not-a-readable-git-repository'})
(HERE/'evidence/source-commits.json').write_text(json.dumps(versions,indent=2)+'\n')
print({r['id']:r['excerpt_line'] for r in rows})
