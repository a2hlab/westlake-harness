#!/usr/bin/env python3
"""Bounded B9 predictor: exact JNI exports + manifest classes + prior service walls.
Presence checks are not semantic proof. It neither changes nor relaxes a gate.
"""
import json,subprocess,hashlib
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[1];W=R/'bms/src/.work/b68-generation'
src=W/'bridge-r155/framework/package-manager/jni/apk_manifest_jni.cpp'
required=['Java_adapter_activity_AppSchedulerBridge_nativeParseManifestJson','Java_adapter_activity_AppSchedulerBridge_nativeGetSysProp']
text=src.read_text();present={s:s in text for s in required}
report={'scope':'B9 selected apps only; not full B10 scanner','input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'jni_source_presence':present,'strict_build_required':True,'exceptions':[], 'ranked_walls':[
 {'rank':1,'id':'manifest-jni','app_count':2,'apps':['fd-android','ooniprobe'],'manifest_classification':'custom Application/content providers','prediction':'native manifest/property entry points available in source; require nm and on-device providers>0','basis':'static source'},
 {'rank':2,'id':'alarm-service','app_count':1,'apps':['fd-android'],'prediction':'likely still blocked after manifest initialization','basis':'prior B5/r8b observations; service-name presence alone is not execution coverage'},
 {'rank':3,'id':'workmanager-provider','app_count':1,'apps':['ooniprobe'],'prediction':'likely still blocked after provider discovery','basis':'prior B5/r8b observations; metadata/provider service behavior remains unverified'},
 {'rank':4,'id':'zigzag-render','app_count':1,'apps':['zigzag'],'prediction':'unknown until screenshot; complete real-work bridge cohort restored','basis':'runtime exception to static prediction; white-window A/B'}],
 'build_inspection':{'required_source_missing_fails':True,'required_minizip_missing_fails':True,'strict_link_no_fallback':True,'source_selection':'real-work source selector, no partial window-only replacement'},
 'service_coverage':'partial: observed walls retained, no full Java service implementation proof', 'deploy_allowed_by_this_report':False,'reason':'advisory prediction; SHA/maps and actual screenshots remain authoritative'}
(E/'prediction.json').write_text(json.dumps(report,indent=2)+'\n')
assert all(present.values());print('prediction rows',len(report['ranked_walls']))
