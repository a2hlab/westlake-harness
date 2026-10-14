#!/usr/bin/env python3
"""Extract frozen implementation evidence without changing live source paths."""
from pathlib import Path
import hashlib, json, re, subprocess, tarfile
ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
DEST = ROOT / 'sources/api-implementations'
REG = json.loads((ROOT/'knowledge/frozen/frozen.json').read_text())
ENTRIES = {e['id']:e for e in REG['entries']}
rows = {}
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args])
def register(fid, rel, data, provenance):
    p=DEST/fid/rel; p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and p.read_bytes()!=data: raise RuntimeError('refuse overwrite: '+str(p))
    p.write_bytes(data)
    row=dict(path=str(p.relative_to(ROOT)),sha256=sha(data),bytes=len(data),**provenance)
    rows.setdefault(fid,[]).append(row)
    return row

def fromgit(fid,ref,path,dest=None):
    commit=git('rev-parse',ref+'^{commit}').decode().strip()
    blob=git('rev-parse',commit+':'+path).decode().strip()
    return register(fid,dest or 'original/'+path,git('cat-file','blob',blob),{'kind':'git_blob','commit':commit,'repo_path':path,'git_blob':blob})

def raw(fid,ref,path):
    # Preserve original author build paths as non-executable recorded evidence.
    return fromgit(fid,ref,path,'build-evidence/'+Path(path).name+'.original.txt')

# FZ001: archive SHA and both contained production binaries bind the source snapshot.
fid='FZ-001';base='benchmark/2026-09-30-installer-background-launcher'
arc=json.loads(git('show','b5a67c62:'+base+'/archive.json'))
archive=ROOT.parent/Path(arc['path']).name
assert sha(archive.read_bytes())==arc['sha256']
with tarfile.open(archive) as tf:
    member={m.name.removeprefix('./'):m for m in tf.getmembers() if m.isfile() and '/._' not in m.name and not Path(m.name).name.startswith('._')}
    binaries={k:sha(tf.extractfile(member['package/'+k]).read()) for k in ['libbms.z.so','libapk_installer.so']}
    assert set(binaries.values())=={a['sha256'] for a in ENTRIES[fid]['artifacts']}
    for name,m in member.items():
        keep=(name in ['base_bundle_installer.cpp','base_bundle_installer.before.cpp'] or
              name.startswith('adapter/framework/package-manager/') and '/tests/' not in name and Path(name).suffix in ('.c','.cpp','.h','.gn') or
              name.startswith('adapter/framework/appspawn-x/bionic_compat/include/') and Path(name).suffix=='.h' or
              name.startswith('adapter/third_party/lodepng/') and Path(name).suffix in ('.cpp','.h') or
              name in ['adapter/build/inner/compile_apk_installer.sh','bms-recipe/build.ninja','bms-recipe/rules.ninja','bms-recipe/libbms.ninja'] or
              name in ['evidence/build-bms.log','evidence/build-installer.log'])
        if not keep: continue
        dest='archive-source/'+name
        if name.endswith(('.sh','.ninja')):dest='build-evidence/'+name+'.original.txt'
        if name.startswith('evidence/'):dest='build-evidence/'+Path(name).name+'.txt'
        register(fid,dest,tf.extractfile(m).read(),{'kind':'verified_archive_member','archive_sha256':arc['sha256'],'archive_name':archive.name,'member':m.name})
    (REPORT/'FZ-001-archive-check.json').write_text(json.dumps({'archive_sha256':arc['sha256'],'archive_bytes':archive.stat().st_size,'contained_frozen_artifact_sha256':binaries,'binaries_extracted':False},indent=2)+'\n')
for name in ['base_bundle_installer.patch','select-launcher.patch','archive.json','source-provenance.json','manifest.json','README.md']:
    dest='patches/'+name if name.endswith('.patch') else 'build-evidence/'+name
    fromgit(fid,'b5a67c62',base+'/'+name,dest)
for name in ['build-bms.sh','build-installer.sh']:raw(fid,'b5a67c62',base+'/'+name)

# FZ002: use source commit identified by the original native freeze audit, not baseline unit.
fid='FZ-002';ref='d8d7a3e0d911bee6549f01fc2234a85d6c23c30e';base='benchmark/2026-09-30-child-stack-default'
for name in ['child_main_after_stock.cpp','child_main.h','adapter_bridge_identity.h','appspawnx_runtime.h']:
    p='bms/src/adapter/framework/appspawn-x/src/'+name
    try:fromgit(fid,ref,p,'src/'+name)
    except subprocess.CalledProcessError:
        if name=='child_main_after_stock.cpp':raise
for name in ['original-commands.json','toolchain.json','results.json','README.md','replacements.json']:
    fromgit(fid,ref,base+'/'+name,'build-evidence/'+name)
raw(fid,ref,base+'/build-provider.sh')
fromgit(fid,ref,'benchmark/2026-09-29-unlocked-generation/source-link-inputs.json','build-evidence/source-link-inputs.json')
fromgit(fid,'2b3960ee','benchmark/2026-09-30-native-freeze-audit/frozen-draft.json','build-evidence/frozen-draft.json')

# Frozen source objects are extracted byte-for-byte and checked against commit:path.
for fid in ['FZ-003','FZ-004','FZ-005','FZ-006','FZ-008']:
    for s in ENTRIES[fid]['sources']:
        if fid=='FZ-005': dest='frozen/'+s['repo_path'].removeprefix('knowledge/toolchains/art-r155/')
        elif fid=='FZ-008':dest='src/android/net/ssl/SSLSockets.java'
        else:dest='src/'+Path(s['repo_path']).name
        row=fromgit(fid,s['commit'],s['repo_path'],dest)
        assert row['git_blob']==s['blob'],(fid,s)
        row['frozen_blob_verified']=True

base='benchmark/2026-09-30-asset-fd-runtime'
for name in ['build.sh','runtime-recipe.sh','restore_b91_cache.py']:raw('FZ-003','8560fd68',base+'/'+name)
for name in ['README.md','object-diff.json','baseline-objects.json','results.json']:
    fromgit('FZ-003','8560fd68',base+'/'+name,'build-evidence/'+name)
for fid,ref,build in [('FZ-004','cdb82fe5','build-result-j1final.json'),('FZ-006','11e3b4c','build-result-j7b.json')]:
    base='benchmark/2026-09-29-bms-link-entry-walls'
    raw(fid,ref,base+'/build.py')
    fromgit(fid,ref,base+'/'+build,'build-evidence/'+build)
    fromgit(fid,ref,'bms/src/adapter/framework/activity/java/B7BindFixes.java','integration/B7BindFixes.java')
    evidence=json.loads((DEST/fid/'build-evidence'/build).read_text())
    frozen=ENTRIES[fid]['sources'][0]
    assert evidence['sources'][frozen['repo_path']]==sha(git('cat-file','blob',frozen['blob']))
    for r in rows[fid]:
        if r.get('frozen_blob_verified'):r['original_build_source_sha_verified']=True
for name in ['recipe/upstream-manifest.md','recipe/README.md','SOURCES.md','T5-NOTES.md']:
    fromgit('FZ-005','HEAD','knowledge/toolchains/art-r155/'+name,'build-evidence/'+name)
for path in ['scripts/lab/reproduce_dex2oat_toolchain.sh','knowledge/toolchains/art-r155/t5_gen_image.sh','knowledge/toolchains/art-r155/recipe/build-host.sh']:
    raw('FZ-005','HEAD',path)
# Preserve the upstream ART notice from the locally identified original r1 tree.
notice=ROOT.parent/'westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/art-r1/NOTICE'
if notice.exists():
    register('FZ-005','licenses/AOSP-art-NOTICE.txt',notice.read_bytes(),{'kind':'local_upstream_notice','logical_source':'westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/art-r1/NOTICE','upstream_base_record':'knowledge/toolchains/art-r155/SOURCES.md'})
base='benchmark/2026-10-01-image-predeploy-gate/t7d-stub-spec'
for name in ['t7d-build-results.json','T7D-STUB-SPEC.md','T7D-BASELINE.md']:
    fromgit('FZ-008','6b2e921',base+'/'+name,'build-evidence/'+name)
(REPORT/'extracted-files.json').write_text(json.dumps({'entries':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'files':len(v),'bytes':sum(r['bytes'] for r in v)} for k,v in rows.items()},indent=2))
