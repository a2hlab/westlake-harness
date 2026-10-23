#!/usr/bin/env python3
"""Bounded ordinary Java/config/checkpoint comparison; no failure attribution."""
import argparse,hashlib,json,re
from pathlib import Path

def need(v,m):
    if not v:raise RuntimeError(m)
def main():
    p=argparse.ArgumentParser();p.add_argument('--tail',type=Path,required=True);p.add_argument('--success',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();ab=a.tail.read_bytes();bb=a.success.read_bytes();ha=hashlib.sha256(ab).hexdigest();hb=hashlib.sha256(bb).hexdigest();need(ha=='dd9c799a1ecc7e0782cf72550eeee1c39fabc5b1b8a8a65d7eeb330e208f107a','tail SHA');need(hb=='2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6','success SHA');al=ab.decode().splitlines();bl=bb.decode().splitlines();need(len(al)==200 and len(bl)==50179,'line bounds')
    def anchors(lines):
        result=[]
        for i,l in enumerate(lines,1):
            m=re.match(r'nullptr\s+\w\s+(\d\d-\d\d)\s+(\d\d:\d\d:\d\d)\s+(\d+)\s+(\d+)\s+',l)
            if m:result.append({'fragment_line':i,'date':m[1],'wall_time':m[2],'pid':int(m[3]),'tid':int(m[4])})
        return result
    needles=[('java_loader_warning','Unsupported class loader'),('java_inline_cache_warning','Missing inline cache for java.lang.Object libcore.reflect.AnnotationMember.copyValue()'),('ordinary_checkpoint','WebView support hold released before onCreate (was false)'),('package_metadata','parsedServices=233 genServices=231 discoveryMeta pre-parcel=-2 post-parcel=-2'),('service_discovery','getServiceInfo HIT com.huawei.agconnect.core.ServiceDiscovery'),('archive_extra_dex','Unable to find entry classes2.dex'),('library_request','path=/data/local/tmp/asx/lib/arm64-v8a/libdelta.so')]
    common=[]
    for category,needle in needles:
        left=[i for i,l in enumerate(al,1) if needle in l];right=[i for i,l in enumerate(bl,1) if needle in l];need(left and right,category+' not shared');common.append({'category':category,'safe_match':needle,'T86_fragment_lines':left,'T95B_fragment_lines':right,'interpretation':'Present in both saved samples; insufficient as a standalone distinguishing cause. Counts are not comparable rates because coverage differs.'})
    # Explicit ordinary Java dependency/configuration exception names only; never inspect process outcomes.
    tokens=['ClassNotFoundException','NoClassDefFoundError','NoSuchMethodError','NoSuchFieldError','Unable to instantiate application','Unable to instantiate activity']
    deps=[]
    for token in tokens:
        deps.append({'token':token,'T86_fragment_lines':[i for i,l in enumerate(al,1) if token in l],'T95B_fragment_lines':[i for i,l in enumerate(bl,1) if token in l]})
    aa=anchors(al);ba=anchors(bl);need({x['pid'] for x in aa}=={7049} and {x['pid'] for x in ba}=={6291},'explicit PID sets')
    meta=[]
    for label,lines,n in [('T86',al,167),('T95B',bl,1171)]:
        m=re.search(r'\bmeta=(-?\d+)',lines[n-1]);need(m,'service metadata');meta.append({'sample':label,'line':n,'meta':int(m[1])})
    need(meta[0]['meta']==meta[1]['meta']==-1,'metadata differs')
    r={'task':'T95C existing ordinary log comparison','status':'SHARED_ORDINARY_WARNINGS_NO_REPRODUCIBLE_INPUT_DIFFERENCE_ESTABLISHED','inputs':{'T86':{'path':'$HOME/.local/share/westlake/existing-launch-output-20261023/raw2/tail.stdout','sha256':ha,'bytes':len(ab),'fragment_lines':len(al)},'T95B':{'path':'$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout','sha256':hb,'bytes':len(bb),'fragment_lines':len(bl),'last_line_partial':not bb.endswith(b'\n')}},'identity':{'T86_explicit_anchors':aa,'T95B_first_last_explicit_anchor':[ba[0],ba[-1]],'T95B_explicit_anchor_count':len(ba),'limit':'Anchors identify distinct PID/wall-clock samples. Untimestamped lines have file context only; boot/birth not independently established from these fragments, and old-line possibility remains.'},'shared_records':common,'service_discovery_metadata':meta,'bounded_java_dependency_token_check':deps,'tail_only_matching_dependency_tokens':[x['token'] for x in deps if x['T86_fragment_lines'] and not x['T95B_fragment_lines']],'conclusion':'Within the named ordinary Java/configuration/checkpoint checks, no reproducible distinguishing input is established. Shared warnings cannot independently explain a different outcome; interactions and other unobserved inputs remain unknown.','coverage_limits':['T86 is a trailing200-line fragment; T95B is a4MiB startup prefix. Missing checkpoint is not non-execution.','All line numbers are fragment-local, not original full-file offsets.','Token checks are bounded, not proof of complete dependency coverage.','No now conversion, timing-difference attribution, exit/signal/memory analysis or patch proposal.'],'privacy':'Only fixed ordinary-message matches and numeric fields exported; raw logs, addresses, URLs and user/network payload omitted.','actions':{'device':0,'REA':0,'new_source':0,'git':0}}
    text=json.dumps(r,indent=2);need(not re.search(r'https?://|0x[0-9a-fA-F]+|/Users/|/home/',text),'privacy');a.output.write_text(text+'\n');print(json.dumps({'status':r['status'],'shared_categories':len(common),'tail_only_dependency_tokens':r['tail_only_matching_dependency_tokens']}))
if __name__=='__main__':main()
