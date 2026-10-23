#!/usr/bin/env python3
"""Reproduce the public, exact-byte T54 source subset from the fixed local intake."""
import argparse, hashlib, json, re, xml.etree.ElementTree as ET
from pathlib import Path
CARD = Path(__file__).resolve().parent
REV = '101781d2eb1097eac5ff57d636af9d7127e5c6e8'
PINS = {'05-exact-manifest.xml':'f471153f4144f82dc35dd3cb1fe0a842937e4301733b6563e3df8f30c07d0e48','03-source-metadata.stdout':'fa88e8cbf5293176adacc2e84b0615b516f4e644f9ff7dee23c6c6a094918013','06-local-changes.patch':'33cc405794a06da8137f3b1cecff6d9bbd0020c5a6b7086389fc9946ffeb0461','04-component.tar.gz':'3d334c1c9f6ad951d7922d60474cd1968794c3e6429d900a5e9cfd3946f9b65c','source-index.json':'477b799ab4c4bea2b3bd73b821de8720071743b9033395e9ac6551c331268d8d'}
# Full files, not excerpts; line ranges identify the reviewed production branches.
FILES = {
'js-context':('frameworks/native/ability/native/ability_runtime/js_ability_context.cpp',[(345,348),(1847,1913),(1915,1929),(2382,2386)]),
'context':('frameworks/native/ability/ability_runtime/ability_context_impl.cpp',[(1596,1604)]),
'connections':('frameworks/native/ability/ability_runtime/connection_manager.cpp',[(56,110),(147,177)]),
'client':('services/abilitymgr/src/ability_manager_client.cpp',[(609,620)]),
'proxy':('services/abilitymgr/src/ability_manager_proxy.cpp',[(1395,1440)]),
'stub':('services/abilitymgr/src/ability_manager_stub.cpp',[(220,229),(1086,1097),(1819,1843)]),
'ams':('services/abilitymgr/src/ability_manager_service.cpp',[(154,159),(354,399),(475,497),(570,575),(5244,5395),(5575,5725),(7932,7995),(10501,10505),(10839,10857),(10898,10981),(11663,11687),(11783,11819),(14594,14649),(16211,16222)]),
'permission':('services/common/src/permission_verification.cpp',[(16,66),(317,320),(352,390),(407,430)]),
'errors':('frameworks/native/ability/native/ability_business_error/ability_business_error.cpp',[(268,284)]),
'error-values':('interfaces/kits/native/ability/native/ability_business_error/ability_business_error.h',[(23,58)]),
'resolve':('services/abilitymgr/src/utils/start_ability_utils.cpp',[(250,303)]),
'bms-helper':('frameworks/native/appkit/ability_bundle_manager_helper/bundle_mgr_helper.cpp',[(244,265),(585,600)]),
'bms-interface-include':('interfaces/kits/native/appkit/ability_bundle_manager_helper/bundle_mgr_helper.h',[(16,24),(69,73)]),
'extension-permissions':('services/abilitymgr/src/utils/extension_permissions_util.cpp',[(25,112)]),
'extension-caller':('services/abilitymgr/src/interceptor/extension_control_interceptor.cpp',[(27,51),(119,142)]),
'other-app-interceptor':('services/abilitymgr/src/interceptor/start_other_app_interceptor.cpp',[(35,80)]),
'connect-manager':('services/abilitymgr/src/ability_connect_manager.cpp',[(325,423)]),
'target-onconnect':('frameworks/native/ability/native/js_service_extension.cpp',[(55,72),(386,425),(622,658)]),
'build-context':('frameworks/native/ability/BUILD.gn',[(46,65)]),
'build-js':('frameworks/native/ability/native/BUILD.gn',[(300,320),(1470,1490)]),
'build-client':('interfaces/inner_api/ability_manager/BUILD.gn',[(65,82)]),
'build-ams':('services/abilitymgr/BUILD.gn',[(14,27),(170,183)]),
'build-ams-files':('services/abilitymgr/abilitymgr.gni',[(16,25)]),
'build-permission':('services/common/BUILD.gn',[(80,102)]),
'sa-profile':('services/sa_profile/180.json',[(1,13)]),
'license':('LICENSE',[(1,14)])}
def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok,msg):
    if not ok: raise ValueError(msg)
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): require(path.read_bytes()==data,'refuse changed output '+str(path.relative_to(CARD)))
    else: path.write_bytes(data)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--intake',type=Path,default=Path.home()/'.local/share/westlake/t54-oh-source-intake-20261023');a=ap.parse_args();root=a.intake
    blobs={f:(root/f).read_bytes() for f in PINS}
    for f,h in PINS.items(): require(sha(blobs[f])==h,'intake drift '+f)
    index={r['path']:r for r in json.loads(blobs['source-index.json'])}
    modified=re.findall(r'^diff --git a/(\S+) b/\S+',blobs['06-local-changes.patch'].decode(),re.M)
    require(len(modified)==5,'unexpected patch scope')
    refs=[]
    for id,(f,ranges) in FILES.items():
        data=(root/'source/ability_runtime'/f).read_bytes();item=index['ability_runtime/'+f]
        require(sha(data)==item['sha256'] and len(data)==item['bytes'],'source index drift '+f)
        require(f not in modified,'reviewed source has local changes '+f)
        dest='sources/ability_runtime/'+f;write(CARD/dest,data)
        require((root/'source/ability_runtime'/f).read_bytes()==data,'source changed during copy '+f)
        lines=data.decode().splitlines();rr=[]
        for lo,hi in ranges:
            require(1<=lo<=hi<=len(lines),'invalid range '+f)
            rr.append({'lines':[lo,hi],'sha256':sha('\n'.join(lines[lo-1:hi]).encode())})
        refs.append({'id':id,'path':dest,'upstream_path':f,'revision':REV,'sha256':sha(data),'bytes':len(data),'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'ranges':rr,'local_patch_member':False})
    for f in ['05-exact-manifest.xml','03-source-metadata.stdout','06-local-changes.patch']:write(CARD/'provenance'/f,blobs[f])
    # T53 is read only. Carry its signed member and accepted conclusions, not private dumps.
    t53=CARD.parent/'2026-10-23-toutiao-service-interface'; prior=json.loads((t53/'results.json').read_text())
    member=(t53/'evidence/t32-signed-module.json').read_bytes();require(sha(member)=='0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51','T53 signed module drift')
    write(CARD/'evidence/t32-signed-module.json',member)
    projects={x.get('name'):dict(x.attrib) for x in ET.fromstring(blobs['05-exact-manifest.xml']).findall('project')}
    report={'schema':1,'task':'T54','status':'GAP','implementation_ready':False,'runtime_verified':False,
      'scope':'Static local source review; no service request, compile, device, remote, REA or T38 execution.',
      'version':{'component':projects['ability_ability_runtime'],'head':REV,'metadata_head_agrees':REV in blobs['03-source-metadata.stdout'].decode(),'modified_files':modified,'reviewed_sources_in_patch':[], 'intake_pins':{f:{'sha256':h,'bytes':len(blobs[f])} for f,h in PINS.items()},'indexed_files':len(index),'selected_files_checked':len(refs),'board_bytes_bound':False,'board_binding_evidence':[],'limitation':'Manifest revision and recorded HEAD agree. Neither proves deployed library bytes, build configuration, or token policy.'},
      'source_refs':refs,
      'paths':[
       {'id':'ordinary-local-service','entry':'UIAbilityContext.connectServiceExtensionAbility','scope':'Normal UIAbility, foreground, same user, explicit local installed target, SERVICE; no free-install, URI-only, remote, UI_SERVICE or APP_SERVICE path.','system_app_direct_rejection':False,'status':'CONDITIONAL_SOURCE_PATH','chain':['js-context','context','connections','client','proxy','stub','ams','resolve','bms-helper','permission','extension-permissions','connect-manager'],'return_semantics':'JS returns connection id before admission. Server errors map to onFailed; even native ERR_OK is not callback completion, bridge work or rendered UI.'},
       {'id':'with-account','entry':'UIAbilityContext.connectServiceExtensionAbilityWithAccount','scope':'Sufficient arguments, current-known normal/non-system caller.','status':'REJECTED_STOPPED','condition':'!TokenIdKit::IsSystemAppByFullTokenID(selfToken)','js_error':202,'refs':['js-context','error-values']}],
      'admission':[
       {'id':'user','refs':['ams','connections'],'condition':'Same-user ordinary route has no blanket system-app check. SERVICE cross-user calls invoke CHECK_CALLER_IS_SYSTEM_APP; IsCrossUserCall and GetValidUserId determine the actual case.','failure':'ERR_NOT_SYSTEM_APP -> 202'},
       {'id':'resolve-type','refs':['ams','resolve'],'condition':'BMS must resolve registered target and correct service type. Normal SERVICE request cannot name arbitrary extensions.','failure':'RESOLVE_ABILITY_ERR -> 16000001; TARGET_ABILITY_NOT_SERVICE / ERR_WRONG_INTERFACE_CALL -> 16000002'},
       {'id':'static-permission','refs':['ams','permission'],'condition':'For an ordinary cross-token caller, target permission list must be empty or every permission granted (existing START_INVISIBLE_ABILITY exception is source behavior, not a proposed grant). Same-token early return is distinct. Requested permissions are not grants.','failure':'ERR_STATIC_CFG_PERMISSION -> 16000005'},
       {'id':'visibility','refs':['permission','ams'],'condition':'Target visible, or same token, or actual START_INVISIBLE_ABILITY authorization. No such elevated grant is established for current host.','failure':'ABILITY_VISIBLE_FALSE_DENY_REQUEST -> 16000004'},
       {'id':'background','refs':['ams','permission'],'condition':'Ordinary SERVICE sets isBackgroundCall=false here; isParamStartAbilityEnable_ may independently reject API>=12 background cross-app UI-only callers under ShouldPreventStartAbility. Foreground passes that particular branch, not all policy.','failure':'CHECK_PERMISSION_FAILED -> 201'},
       {'id':'policy','refs':['ams','extension-caller','other-app-interceptor','extension-permissions'],'condition':'Forbid-start, DLP build flag, before/after interceptors, user availability, service manager and preload errors still propagate. Normal UIAbility is not subject to the other-extension caller restriction; StartOtherApp isWithUI=false returns early. No claim that installed configuration passes every interceptor.','failure':'Actual native error propagated; see errors map'}],
      'capability':{'caller':'conditional_source_path','target_registration':'unknown','target_runtime_eligibility':'unknown','bridge_endpoint':'unknown','permission_sufficiency':'unknown','normal_host_can_register_service_proven':False,'bridge_endpoint_found':False},
      'missing_parts':[
       {'id':'bms-registration','status':'unknown','component':projects['bundlemanager_bundle_framework'],'local_intake_available':True,'peer_review':'pending cx-env bms-admission; no duplicate BMS scan','actual_reference':'bundle_mgr_helper.h:21 includes bundle_mgr_interface.h; helper.cpp:599 calls IBundleMgr::QueryExtensionAbilityInfos; services/abilitymgr/BUILD.gn:177-179 depends on bundle_framework.','needed':'Same-revision BMS registration/install validation and query implementation determining SERVICE eligibility from signed profile/application privilege; concrete registered target metadata. Internal server filename not established by this intake.','refs':['bms-interface-include','bms-helper','build-ams','resolve']},
       {'id':'token-backend','status':'unknown','component':projects['security_access_token'],'local_intake_available':False,'actual_reference':'permission_verification.cpp:19 includes accesstoken_kit.h; lines45/63 call VerifyAccessToken; services/common/BUILD.gn:92-93 links access_token libraries.','needed':'Same-revision backend if its grant decisions must be established; actual caller-target token/permission evidence remains separate.','refs':['permission','build-permission']},
       {'id':'owned-bridge-target','status':'unknown','needed':'Concrete supported target bundle/module/ability, registration evidence, service onConnect remote interface/transaction implementation, authorization and bridge operation/build provenance. Framework RemoteObject transport supplies none of these by itself.','refs':['target-onconnect','connect-manager']},
       {'id':'board-binding','status':'unknown','needed':'Deployed ability runtime/BMS/access-token artifact identities, build/config provenance tying them to these sources. No new collection performed.','refs':['build-ams','build-permission','sa-profile']}],
      't53':{'accepted_commit':'0a52f405ec','report_sha256':sha((t53/'results.json').read_bytes()),'signed_manifest':{'path':'evidence/t32-signed-module.json','sha256':sha(member),'extension_abilities':[]},'caller_observation':prior['caller_observation'],'historical_caller_source':next(x for x in prior['source_refs'] if x['id']=='t52-caller'),'note':'Historical 2026-10-22 sample, not fresh authority. requestPermissions does not imply permissions granted.'},
      'minimum_prerequisites':['Resolve BMS registration eligibility at pinned manifest component and bind a concrete installed target.','Supply an existing supported bridge service implementation and its caller authorization; do not infer it from generic AMS transport.','Bind deployed sources/configuration and actual caller-target permissions before an implementation-ready assessment.','Application UI reentry and bridge runtime reconstruction are different operations; this card proves no reconstruction endpoint.']}
    peer_path=CARD/'provenance/bms-admission.json'
    peer_bytes=peer_path.read_bytes();require(sha(peer_bytes)=='fae9099aa5e34b5cdec4812a8bde677678839c2d2fd02ce38f387ada879247c3','BMS peer changed')
    peer=json.loads(peer_bytes)
    bms_pins={'07-bms-metadata':'563136a45cdc15601107ad12f192905595800a9b5feaeac923e813815260930c','09-bms-changes.patch':'74dc41a5ad00c03fe2c8b4cccf7730acb00e3328bd624d212cf1c8e64074bc75','08-bms-source.tar.gz':'38e723e2e1347a36e020c6205494a42ded766c715281dc5be6ddae03ab63a6b6'}
    for f,h in bms_pins.items():
        data=(root/f).read_bytes();require(sha(data)==h,'BMS intake drift '+f)
        if f!='08-bms-source.tar.gz':write(CARD/'provenance'/f,data)
    bix_bytes=(root/'bms-source-index.json').read_bytes();bix={x['path']:x for x in json.loads(bix_bytes)}
    bms_refs=[]
    for id,item in peer['source_evidence'].items():
        f=item['path'].split('/source/bundle_framework/',1)[1];data=(root/'source/bundle_framework'/f).read_bytes()
        require(sha(data)==item['sha256'],'BMS peer source drift '+f)
        ix=bix['bundle_framework/'+f];require(sha(data)==ix['sha256'] and len(data)==ix['bytes'],'BMS source index drift '+f)
        dest='sources/bundle_framework/'+f;write(CARD/dest,data)
        require((root/'source/bundle_framework'/f).read_bytes()==data,'BMS changed while copying '+f)
        lines=data.decode().splitlines();ranges=[]
        for lo,hi in item['lines']:
            require(1<=lo<=hi<=len(lines),'BMS range invalid')
            ranges.append({'lines':[lo,hi],'sha256':sha('\n'.join(lines[lo-1:hi]).encode())})
        ref={'id':'bms-'+id,'path':dest,'upstream_path':f,'revision':projects['bundlemanager_bundle_framework']['revision'],'sha256':sha(data),'bytes':len(data),'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'ranges':ranges,'local_patch_member':f in peer['provenance']['patch_changed_files'],'source_index_match':True}
        refs.append(ref);bms_refs.append(ref['id'])
    report['version']['selected_files_checked']=26
    report['bms_review']={'peer_sha256':sha(peer_bytes),'peer_path':'provenance/bms-admission.json','component':projects['bundlemanager_bundle_framework'],'source_refs':bms_refs,'recorded_head':peer['provenance']['recorded_head'],'modified_files':peer['provenance']['patch_changed_files'],'selected_modified_refs':['bms-installer','bms-build'],'input_pins':bms_pins,'bms_source_index':{'sha256':sha(bix_bytes),'bytes':len(bix_bytes),'entries':len(bix),'selected_matches':8},'peer_original_index_note':'Peer null matches used the ability_runtime-only index. This card checked the new separate BMS index for the eight selected files.','registration_rule':'SERVICE requires effective allowUsePrivilegeExtension; not a system-only predicate. APP_SERVICE is in neither reviewed type set, not proof of full install or connection eligibility.','effective_build_arg':'unknown','target_effective_privilege_capability':'unknown','complete_registration_eligibility':'unknown','findings':peer['findings']}
    report['capability']['registration_rule']='source_bound_privilege_capability_gate'
    gap=report['missing_parts'][0];gap['peer_review']='bound eight source files; registration rule established, actual eligibility unknown'
    gap['needed']='Actual deployed USE_PRE_BUNDLE_PROFILE/build binding, target signed provision and matching preinstall capability entry; generic installation validity and concrete registered target remain unproved. No further BMS source requested for this bounded rule.'
    gap['refs']+=bms_refs
    report['minimum_prerequisites'][0]='Bind actual BMS build arguments and target effective privilege capability/registration; SERVICE capability gate is source-established, current target eligibility is not.'
    # Historical locator remains evidence provenance, not a rerun dependency.
    write(CARD/'results.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({'status':'GAP','source_files':len(refs),'source_bytes':sum(r['bytes'] for r in refs),'results_sha256':sha((CARD/'results.json').read_bytes())}))
if __name__=='__main__':main()
