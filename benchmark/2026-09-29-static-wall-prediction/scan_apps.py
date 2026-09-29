#!/usr/bin/env python3
"""Conservative, offline APK callsite scan. Never equates references with reachability."""
import concurrent.futures, csv, hashlib, json, re, subprocess, tempfile, zipfile
from pathlib import Path
from scan_jni import HERE, BASE, DEXDUMP, sha
from scan_io import load
INPUT=BASE/'westlake-harness-b4/benchmark/2026-09-29-manifest-classes'
# Android API class names; unresolved/obfuscated class constants remain unknown.
CLASS_SERVICE={'UserManager':'user','NotificationManager':'notification','AlarmManager':'alarm','UiModeManager':'uimode','LocaleManager':'locale','AccountManager':'account','AppOpsManager':'appops','ClipboardManager':'clipboard','PowerManager':'power','AudioManager':'audio','ConnectivityManager':'connectivity','LocationManager':'location','InputMethodManager':'input_method','WindowManager':'window','DisplayManager':'display','ActivityManager':'activity','LayoutInflater':'layout_inflater','SensorManager':'sensor','Vibrator':'vibrator','VibratorManager':'vibrator_manager','TelephonyManager':'phone','WifiManager':'wifi','JobScheduler':'jobscheduler','StorageManager':'storage','CameraManager':'camera','DownloadManager':'download','KeyguardManager':'keyguard','AccessibilityManager':'accessibility','SearchManager':'search','NfcManager':'nfc','BluetoothManager':'bluetooth','TextServicesManager':'textservices','DevicePolicyManager':'device_policy','FingerprintManager':'fingerprint','BiometricManager':'biometric','InputManager':'input','RoleManager':'role','PermissionManager':'permissionmgr'}
HEADER=re.compile(r'\|\[[0-9a-f]+\] (.+)')
INSN=re.compile(r'\|([0-9a-f]{4,}): (.+)')
INVOKE=re.compile(r'(invoke-[\w/-]+) \{([^}]+)\}, L([^;]+);\.([^:]+):(\([^ ]+)')
FEATURES={'koin':'org/koin/','workmanager':'androidx/work/','sqlite':'android/database/sqlite/','jna':'com/sun/jna/','appcompat':'androidx/appcompat/','flutter':'io/flutter/'}

def method_scan(method, insns, dex, linebase, native_ids):
    # Target offsets are joins. Any method with switch/catch is conservative:
    # reset all constants at targets, and after branches; catch handlers start move-exception.
    targets=set()
    for _,_,text in insns:
        if text.startswith(('if-','goto')):
            m=re.search(r'(?:, |goto(?:/\w+)? )([0-9a-f]+) //',text)
            if m:targets.add(m[1].lstrip('0') or '0')
    has_switch=any('switch ' in t for _,_,t in insns)
    regs={};calls=[];native=[];features={}
    for offset,line,text in insns:
        if offset.lstrip('0') in targets or (offset.lstrip('0') or '0') in targets:regs={}
        for feature,needle in FEATURES.items():
            if needle in text and feature not in features:features[feature]={'dex':dex,'method':method,'offset':offset,'line':line,'text':text}
        inv=INVOKE.search(text)
        if inv:
            op,args,cls,name,sig=inv.groups();mid=f'{cls}.{name}{sig}'
            if mid in native_ids:native.append({'id':mid,'dex':dex,'method':method,'offset':offset,'text':text})
            if name=='getSystemService' or (cls=='android/os/ServiceManager' and name in ['getService','checkService','waitForService']):
                rr=re.findall(r'v\d+',args)
                if '..' in args and len(rr)==2:rr=[f'v{i}' for i in range(int(rr[0][1:]),int(rr[1][1:])+1)]
                formal=re.findall(r'\[*L[^;]+;|\[*[ZBCSIJFD]',sig[1:sig.index(')')])
                positions=[];slot=0 if op.startswith('invoke-static') else 1
                for param in formal:
                    if param in ['Ljava/lang/String;','Ljava/lang/Class;']:positions.append(slot)
                    slot+=2 if param in ['J','D'] else 1
                arg=positions[0] if len(positions)==1 else -1
                value=regs.get(rr[arg]) if 0<=arg<len(rr) and not has_switch else None
                service=None;kind=None
                if value:
                    kind,v=value
                    service=v if kind=='string' else CLASS_SERVICE.get(v.rsplit('/',1)[-1].strip(';'))
                calls.append({'service':service or 'unknown','argument':value,'reason':'straight-line constant argument' if service else 'unresolved argument/class mapping or control-flow join; no interprocedural guess','dex':dex,'method':method,'offset':offset,'line':line,'text':text})
        m=re.match(r'const-string(?:/jumbo)? (v\d+), "(.*)" //',text)
        c=re.match(r'const-class (v\d+), L([^;]+);',text)
        mv=re.match(r'move-object(?:/\w+)? (v\d+), (v\d+)',text)
        if m:regs[m[1]]=('string',m[2])
        elif c:regs[c[1]]=('class',c[2])
        elif mv:
            regs.pop(mv[1],None)
            if mv[2] in regs:regs[mv[1]]=regs[mv[2]]
        elif not text.startswith(('invoke-','if-','goto','return','iput','sput','aput','monitor-','check-cast')):
            dest=re.match(r'[^ ]+ (v\d+)',text)
            if dest:regs.pop(dest[1],None)
        if text.startswith(('if-','goto','return','throw','move-exception')) or 'switch ' in text:regs={}
    return calls,native,features

def scan(app,native_ids):
    key=app['key'];apk=INPUT/'apks'/key/(key+'.apk');calls=[];natives=[];features={};dexes=[]
    with tempfile.TemporaryDirectory(prefix='b10-apk-') as td, zipfile.ZipFile(apk) as z:
        libs=[n for n in z.namelist() if n.startswith('lib/') and n.endswith('.so')]
        for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
            data=z.read(entry);path=Path(td)/entry;path.write_bytes(data)
            dexes.append({'entry':entry,'sha256':hashlib.sha256(data).hexdigest()})
            proc=subprocess.Popen([str(DEXDUMP),'-d',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
            method='';insns=[]
            def flush():
                c,n,f=method_scan(method,insns,entry,0,native_ids);calls.extend(c);natives.extend(n)
                for k,v in f.items():features.setdefault(k,v)
            for lineno,line in enumerate(proc.stdout,1):
                h=HEADER.search(line)
                if h:flush();method=h[1];insns=[]
                m=INSN.search(line)
                if m:insns.append((m[1],lineno,m[2]))
            flush();err=proc.stderr.read();rc=proc.wait()
            if rc:raise RuntimeError(f'{apk}:{entry}: {err}')
    result={'key':key,'apk':str(apk),'sha256':sha(apk),'dexes':dexes,'manifest':app,'calls':calls,'native_calls':natives,'features':features,'native_libraries':libs}
    (HERE/'evidence'/f'app-{key}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(key,len(calls),len(natives),flush=True);return result

def load_apps():
    data=load(HERE/'app-results.json')
    if isinstance(data,list):return data
    return [load(HERE/x['evidence']) for x in data['apps']]

def main():
    matrix=json.loads((HERE/'jni-results.json').read_text());ids={m['id'] for x in matrix.values() for m in x['methods']}
    apps=json.loads((INPUT/'results.json').read_text())['apps']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda a:scan(a,ids),apps))
    (HERE/'app-results.json').write_text(json.dumps({'apps':[{'key':r['key'],'sha256':r['sha256'],'evidence':'evidence/app-'+r['key']+'.json'} for r in results]},indent=2)+'\n')
if __name__=='__main__':main()
