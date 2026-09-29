"""Static conditional installer requirement. Never reads app-key outcome labels."""
import re
FAMILY='installer-background-start'
PERMISSION='ohos.permission.START_ABILITIES_FROM_BACKGROUND'

def enabled(node):
    return str(node.get('attrs',{}).get('enabled','true')).lower() not in {'false','0','0x00000000'}

def detect(manifest,activities,activity_calls=(),permission='unknown'):
    if permission not in {'absent','granted','unknown'}:raise ValueError('invalid permission state')
    nodes=[n for n in activities if enabled(n)]
    entries=manifest.get('launchers',[])
    roots={e['class'].replace('.','/') for e in entries}
    entry_lines={e.get('line') for e in entries}
    aliases=[n for n in nodes if n.get('tag')=='activity-alias' and n.get('line') in entry_lines]
    # Resolve aliases, but an alias redirect is not an in-app startActivity call.
    for n in aliases:
        roots.discard(n['class'])
        if n.get('target'):roots.add(n['target'])
    declared={n['class'] for n in nodes if n.get('tag')=='activity'}
    hints=[]
    for root in sorted(roots):
        short=root.rsplit('/',1)[-1]
        targets=sorted(declared-roots)
        if re.search(r'IntentHandler',short,re.I) and targets:kind='intent-handler-entry'
        elif re.search(r'Splash|Startup|Launch',short,re.I) and any(re.search(r'MainActivity|HomeActivity|MainScreen',t.rsplit('/',1)[-1],re.I) for t in targets):kind='splash-to-main-candidate'
        else:continue
        hints.append({'kind':kind,'entry':root,'possible_targets':targets,'manifest_lines':[e['line'] for e in entries if e['class'].replace('.','/')==root]+[n['line'] for n in nodes if n['class'] in targets]})
    calls=[]
    for call in activity_calls:
        targets=[t for t in call.get('non_launcher_targets',[]) if t in declared-roots]
        hinted=[t for t in call.get('class_hints',[]) if t in declared-roots]
        if not targets and not hinted:continue
        reached=call.get('startup_reachable')=='conditional-static'
        calls.append({'method':call['method'],'dex':call['dex'],'line':call['line'],'targets':targets,'class_hints':hinted,'startup_reachable':call.get('startup_reachable','unknown'),'strength':'explicit-startup-target' if reached and targets else 'callback-or-target-candidate','finish_order':call.get('finish_lexical_order'),'api':call.get('api')})
    strong=any(c['strength']=='explicit-startup-target' for c in calls)
    risk=bool(hints or calls)
    status=('no-static-hit' if not risk else 'permission-requirement-satisfied' if permission=='granted' else 'conditional-installer-wall' if permission=='absent' else 'requires-installer-grant-check')
    return {'family':FAMILY,'permission':PERMISSION,'installer_permission_state':permission,'status':status,'static_risk':risk,'manifest_risk':bool(hints),'strength':'explicit-startup-target' if strong else 'candidate' if risk else 'no-static-hit','launchers':sorted(roots),'launcher_aliases':aliases,'manifest_hints':hints,'dex_witnesses':calls,'stub_ok':False,'needs_real':risk,'runtime_limit':'Manifest naming/cached call paths do not prove execution, background timing or a denied window. Alias alone does not imply a second Activity. StartAbility=0 may precede asynchronous WMS denial.'}
