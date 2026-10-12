#!/usr/bin/env python3
"""Build measured 5cd disabled binding locally. No transport is imported/created."""
import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_v2',HERE.parent/'restore-v2/toutiao_provider.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
E=p.WS/'westlake-harness/benchmark/2026-10-12-v1-seal-execution'

def ref(path):
    path=Path(path).resolve()
    return {'path':'$WORKSPACES/'+str(path.relative_to(p.WS)),'sha256':p.digest(path)}

def save(name,obj):
    p.write(HERE/name,obj)

def captured(stem):
    raw=E/(stem+'.stdout');record=E/(stem+'.json')
    j=p.read(record);text=raw.read_text().replace('\r','')
    p.need(j['exit']==0 and j['stdout_sha256']==p.digest(raw),'capture transport/hash')
    lines=text.splitlines();p.need(lines[-1]=='RE_REMOTE_RC=0','capture remote rc')
    return j,text,{'record':ref(record),'stdout':ref(raw)}

def main():
    fragment=p.read(HERE.parent/'restore-v2/runtime-inputs.json')
    pre=p.read(E/'restore-5cd-preimages/results.json')
    root='/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012'
    b={k:copy.deepcopy(fragment[k]) for k in ('runtime_root','stage_root','host_uid','runtime_archive','runtime_closure','runtime_file_metadata','extra_runtime_files','new_storage_directories','storage')}
    b.update(schema='route-b-restore-binding/v2',serial=pre['serial'],boot_id=pre['boot_id'],attempt_root=root,
             socket=p.OLD_SOCKET,startup_enabled=False,before={},after={},directories=[],stage_files=[],
             required_directories=[],tools=p.read(p.RELEASE/'plan.disabled.json')['tools'],
             release_inventory=ref(p.RELEASE/'checkpoint-manifest.json'),exe_alias_manifest=ref(p.ALIASES/'manifest.json'),
             host_hap={'path':'$HOME/a2hlab-provision/ttbundle/source-host.hap','sha256':p.HAP_SHA})
    oldplan=p.read(p.RELEASE/'plan.disabled.json')
    _,raw,dirpins=captured('restore-5cd-preimages/028-directories')
    lines=raw.splitlines(); dirs={}
    for n,line in enumerate(lines):
        if not line.startswith('PATH='):continue
        target=line[5:]
        if lines[n+1]=='ABSENT':dirs[target]={'exists':False,'proof':'measured absence '+dirpins['stdout']['path']+' SHA='+dirpins['stdout']['sha256']}
        else:
            mode,uid,gid=lines[n+1].split(':');labels=[x for x in lines[n+2].split() if x.startswith('u:object_r:')]
            p.need(len(labels)==1,'directory label')
            dirs[target]={'exists':True,'after':dict(mode=mode,uid=int(uid),gid=int(gid),label=labels[0])}
    for t,d in dirs.items():
        if d['exists']:b['required_directories'].append({'target':t,**d})
    b['storage']['stage']=copy.deepcopy(dirs[p.OLD_STAGE])
    rootmeta={'mode':'750','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
    for t in (str(Path(root).parent),root):b['directories'].append({'target':t,'before':dirs[t],'after':dict(rootmeta)})
    for t in ('/data/westlake-demo/toutiao','/data/westlake-demo/toutiao/scripts','/data/local/tmp/operator45/selfheal48'):
        label='u:object_r:data_local_tmp:s0' if t.startswith('/data/local/tmp/') else rootmeta['label']
        b['new_storage_directories'].append({'target':t,'before':dirs[t],'after':dict(rootmeta,label=label),
            'metadata_basis':'explicit new control directory creation policy; pinned executor 750/root plus observed target ancestor label'})
    b['new_storage_directories'].append({'target':p.OLD_STAGE,'before':dirs[p.OLD_STAGE],
        'after':{'mode':'755','uid':0,'gid':0,'label':'u:object_r:data_local_tmp:s0'},
        'metadata_basis':'PROPOSED new stage creation policy: root-owned traversable tools directory, target ancestor data_local_tmp label; not observed existing 5cd stage'})
    for row in oldplan['members']:
        target=row['target'].replace(p.OLD_ROOT,root)
        before=copy.deepcopy(pre['files'][target]);p.need(before['exists'] is False,'unexpected control preimage')
        before['proof']='measured target absence in '+ref(E/'restore-5cd-preimages/results.json')['path']+' SHA='+p.digest(E/'restore-5cd-preimages/results.json')
        b['before'][target]=before;b['after'][target]=copy.deepcopy(row['after'])
    stop=copy.deepcopy(pre['files'][p.OLD_STOP]);stop['proof']='measured old stop absent; same pinned 5cd preimages'
    b['preserved']=[{'target':p.OLD_STOP,'before':stop}]
    hap='/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
    b['prerequisites']=[{'target':hap,'sha256':pre['files'][hap]['sha256']}]
    # Normalize actual historical donor stage probes, retaining raw provenance.
    # These are donor after metadata, never an assertion that 5cd stage exists.
    _,bootbefore,bp=captured('alias-transaction/001-boot')
    _,bootafter,ap=captured('alias-transaction/084-boot')
    p.need(bootbefore==bootafter,'stage donor observation boot changed')
    observations={'serial':p.OLD_SERIAL,'boot_id':bootbefore.splitlines()[0],'stable_boot':True,
                  'basis':'historical donor stage; target5cd absent; no current5cd deployment claimed','boot_provenance':[bp,ap],'files':[]}
    source_root=p.WS/'westlake-harness/benchmark/2026-10-12-toutiao-recovery-integration/sources'
    sources={'source_app_namespace':source_root/'source_app_namespace','host_spawn':source_root/'host_spawn',
             'request.bin':p.RELEASE/'payload/request-uid20011206.bin'}
    for name,number in [('request.bin','080'),('source_app_namespace','082'),('host_spawn','083')]:
        record,text,provenance=captured('alias-transaction/'+number+'-probe')
        p.need(record['argv'][2]==p.OLD_SERIAL,'stage donor serial')
        rows=text.splitlines();p.need(rows[0]=='EXISTS','donor stage missing')
        mode,uid,gid=rows[1].split();sha,target=rows[2].split();label=[x for x in rows[3].split() if x.startswith('u:object_r:')][0]
        p.need(target==p.OLD_STAGE+'/'+name and p.digest(sources[name])==sha,'stage local bytes differ from donor')
        meta=dict(mode=mode,uid=int(uid),gid=int(gid),label=label)
        observations['files'].append(dict(meta,target=target,sha256=sha,observed=True,provenance=provenance))
        b['stage_files'].append({'target':target,'source':ref(sources[name]),'after':meta,'before':copy.deepcopy(dirs[p.OLD_STAGE])})
    save('stage-donor-observations.json',observations)
    for row in b['stage_files']:row['metadata_evidence']={**ref(HERE/'stage-donor-observations.json'),'target':row['target']}
    # Pin current SHA observations independently; never label archive bytes live.
    current=p.read(E/'restore-runtime-sha/index.json');live=p.read(E/'restore-live-scripts/index.json')
    archive=p.read(p.resolve(b['runtime_archive']['path'],HERE));indexed={r['target']:r for r in archive['files']}
    p.need(current['stable_boot'] and current['count']==221 and current['matched']==218,'current SHA capture shape')
    expected={p.OLD_RT+'/'+n for n in ('run.sh','preseed_metasec48.sh','prepare_jit50.sh')}
    p.need(set(current['mismatches'])==expected,'unexpected runtime drift')
    for t,r in indexed.items():
        if t not in expected:p.need(r['sha256']==current['observed'][t],'non-script current drift')
    audit=[]
    for row in live['files']:
        target=row['target'];name=Path(target).name;old=indexed[target]
        source=p.pin({'path':old['source'],'sha256':old['sha256']},HERE)
        now=p.pin({'path':row['source'],'sha256':row['sha256']},HERE)
        p.need(current['observed'][target]==row['sha256'],'live/current SHA mismatch')
        before=source.read_bytes();observed=now.read_bytes()
        exact=before.replace(b'20010053',b'20011206')
        if name=='run.sh':exact=exact.replace(b'export WL_PARENT_ID=1443',b'export WL_PARENT_ID=33')
        p.need(exact==observed,'unexpected live script change')
        def derive(data):
            data=p.derive_text(data.replace(b'20010053',b'20011300'),b)
            if name=='run.sh':data=re.sub(rb'export WL_PARENT_ID=[0-9]+',b'export WL_PARENT_ID=0',data)
            return data
        final=derive(before);p.need(final==derive(observed),'archive/live derivation differs')
        audit.append({'target':target,'archive_sha256':old['sha256'],'current61b_sha256':row['sha256'],
          'derived5cd_sha256':hashlib.sha256(final).hexdigest(),'derive_from_archive_and_live_equal':True,
          'diff_archive_to_live':''.join(difflib.unified_diff(before.decode().splitlines(True),observed.decode().splitlines(True))),
          'diff_live_to_5cd':''.join(difflib.unified_diff(observed.decode().splitlines(True),final.decode().splitlines(True)))})
    save('script-derivation-audit.json',{'observations':[ref(E/'restore-runtime-sha/index.json'),ref(E/'restore-live-scripts/index.json')],
        'files':audit,'wid_policy':'0 template; verified current WID supplied by launch-common to bounded helper; never copy33'})
    b['observation_provenance']={'target_preimages':ref(E/'restore-5cd-preimages/results.json'),'target_directories':dirpins,
       'current_runtime_sha':ref(E/'restore-runtime-sha/index.json'),'live_scripts':ref(E/'restore-live-scripts/index.json'),
       'control_after_policy':ref(p.RELEASE/'plan.disabled.json'),'stage_after_policy':'historical donor file metadata; new root policy explicit',
       'not_authorized_for_execution':True}
    save('binding.5cd.disabled.json',b)
    print(json.dumps({'status':'DISABLED_BINDING','members_expected':len(oldplan['members'])+460+3,'stage':len(b['stage_files']),'directories':len(b['directories'])+len(b['new_storage_directories']),'startup_enabled':False}))

if __name__=='__main__':main()
