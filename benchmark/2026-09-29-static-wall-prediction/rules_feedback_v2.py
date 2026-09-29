"""Outcome-independent conditional requirements; no app-key allowlists."""
import re,sys
from pathlib import Path
BG=Path(__file__).resolve().parents[1]/'2026-09-30-background-start-prospective'
sys.path.insert(0,str(BG))
from detector import inspect_method as inspect_activity,resolve_intent
from scan_apps import INVOKE
FAMILIES=('authorized-secondary-activity','boot-conscrypt-fallback','egl-window-recreation')
PROVIDER='com.android.org.conscrypt.OpenSSLProvider'

def provider_api(owner,name,sig):
    if owner=='java/util/ServiceLoader' and name in {'load','loadInstalled','iterator','stream'}:return 'service-loader-resource-verification'
    if owner in {'java/util/jar/JarFile','java/util/jar/JarInputStream'} and name in {'<init>','getInputStream','getNextJarEntry'}:return 'jar-verification'
    if owner=='sun/security/jca/Providers' and name=='getSunProvider':return 'direct-boot-provider'
    if owner=='java/lang/ClassLoader' and name in {'getResource','getResources','getResourceAsStream'}:return 'classloader-resource-candidate'
    if owner=='java/lang/Class' and name=='getResourceAsStream':return 'classloader-resource-candidate'
    return None

def inspect(method,dex,insns):
    rows=inspect_activity(method,dex,insns)
    # Obfuscated ActivityResultLauncher subclasses are validated against hierarchy later.
    for off,line,text in insns:
        inv=INVOKE.search(text)
        if not inv:continue
        kind,args,owner,name,sig=inv.groups()
        reason=provider_api(owner,name,sig)
        loc=dict(method=method,dex=dex,offset=off,line=line,text=text)
        if reason:rows.append(dict(kind='provider',reason=reason,api=owner+'.'+name+sig,**loc))
        if owner in {'java/lang/Class','java/lang/ClassLoader'} and name in {'forName','loadClass'}:
            literals=[dict(offset=o,line=n,text=t) for o,n,t in insns if 'const-string' in t and PROVIDER in t]
            if literals:rows.append(dict(kind='provider',reason='provider-name-reflection-candidate',api=owner+'.'+name+sig,literals=literals,**loc))
        if name=='launch' and ('Ljava/lang/Object;' in sig or 'Landroid/content/Intent;' in sig) and (not owner.startswith('androidx/activity/result/') or 'Landroid/content/Intent;' in sig):
            translated=[(o,n,t.replace('L'+owner+';.launch:', 'Landroidx/activity/result/ActivityResultLauncher;.launch:').replace('(Landroid/content/Intent;', '(Ljava/lang/Object;')) if o==off else (o,n,t) for o,n,t in insns]
            for r in inspect_activity(method,dex,translated):
                if r['kind']=='start' and r['offset']==off:rows.append({**r,'api':owner+'.'+name+sig,'launcher_owner_candidate':owner,'text':text})
    return rows

def subtype(cls,base,parents,interfaces):
    todo=[cls];seen=set()
    while todo:
        c=todo.pop()
        if c==base:return True
        if not c or c in seen:continue
        seen.add(c);todo.extend([parents.get(c)]+interfaces.get(c,[]))
    return False

def activity_rows(extras,nodes,launchers,parents,interfaces,paths):
    activities={n['target'] or n['class'] for n in nodes}
    factories={x['method']:x['returns'] for x in extras if x['kind']=='factory'}
    out=[]
    for x in extras:
        if x['kind']!='start':continue
        if x.get('launcher_owner_candidate') and not subtype(x['launcher_owner_candidate'],'androidx/activity/result/ActivityResultLauncher',parents,interfaces):continue
        targets,proof=resolve_intent(x.get('intent'),factories)
        nonlaunch=[t for t in targets if t in activities and t not in launchers]
        hints=sorted({h['class_name'] for h in x.get('class_hints_same_method',[]) if h['class_name'] in activities-launchers})
        caller=x['method'].split('.',1)[0]
        is_entry=caller in launchers or any(subtype(l,caller,parents,interfaces) for l in launchers)
        reached=x['method'] in paths
        # No callback/branch inference: hints are candidates, even in lifecycle bodies.
        candidate=bool((nonlaunch or hints) and (reached or re.search('Splash|Launch|Startup',caller,re.I)))
        if not candidate:continue
        out.append({**x,'resolved_targets':targets,'non_launcher_targets':nonlaunch,'class_hints':hints,'resolution':proof,
                    'startup_reachable':'conditional-static' if reached else 'unknown-callback',
                    'entry_class':is_entry,'verdict':'explicit-startup-target' if nonlaunch and reached else 'callback-or-target-candidate',
                    'control_flow':'lexical finish order only; no dominance/branch execution proof'})
    return out

def boot_visibility(boot_classes,runtime_classes):
    name=PROVIDER.replace('.','/')
    return {'class':PROVIDER,'boot_definition':name in boot_classes,'runtime_definition':name in runtime_classes,
            'verification_fallback_boot_definition':'sun/security/provider/VerificationProvider' in boot_classes,
            'boot_lookup':'definition-present-resolution-unknown' if name in boot_classes else 'missing-in-pinned-boot-jars',
            'runtime_definition_repairs_boot_lookup':False}
