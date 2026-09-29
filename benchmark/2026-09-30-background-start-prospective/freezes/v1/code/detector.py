"""Bounded register witnesses for explicit Android Activity transitions."""
import copy,re
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-09-29-static-wall-prediction'
sys.path.insert(0,str(OLD))
from scan_apps import INVOKE
STARTS={'startActivity','startActivityForResult','startActivities','startActivityIfNeeded','startActivityFromChild','startActivityFromFragment'}
FINISH={'finish','finishAffinity','finishAfterTransition','finishAndRemoveTask'}

def registers(text):
    rr=re.findall(r'v\d+',text)
    if '..' in text and len(rr)==2:return ['v'+str(n) for n in range(int(rr[0][1:]),int(rr[1][1:])+1)]
    return rr

def inspect_method(method,dex,insns):
    regs={};last=None;rows=[];finish=[];class_hints=[];returns=[];joins=set()
    for offset,line,text in insns:
        if text.startswith(('if-','goto')):
            m=re.search(r'(?:, |goto(?:/\w+)? )([0-9a-f]+) //',text)
            if m:joins.add(int(m[1],16))
    # Switch/catch feasibility is never inferred; block resets lose information.
    for offset,line,text in insns:
        if int(offset,16) in joins:regs={};last=None
        loc=dict(method=method,dex=dex,offset=offset,line=line,text=text)
        inv=INVOKE.search(text)
        if inv:
            op,args,owner,name,sig=inv.groups();rr=registers(args);mid=owner+'.'+name+sig;last=None
            values=[regs.get(x) for x in rr]
            receiver=values[0] if values and not op.startswith('invoke-static') else None
            if owner=='android/content/Intent' and name=='<init>' and rr:
                obj=regs.get(rr[0])
                if not obj or obj.get('kind')!='intent':obj={'kind':'intent','target':None};regs[rr[0]]=obj
                if 'Ljava/lang/Class;' in sig:
                    classes=[v['value'] for v in values[1:] if v and v.get('kind')=='class']
                    if len(classes)==1:obj['target']=classes[0]
            elif owner=='android/content/Intent' and name in {'setClass','setClassName','setComponent'} and isinstance(receiver,dict):
                classes=[v['value'] for v in values[1:] if v and v.get('kind')=='class']
                components=[v['target'] for v in values[1:] if v and v.get('kind')=='component']
                strings=[v['value'] for v in values[1:] if v and v.get('kind')=='string']
                target=(classes+components)[0] if len(classes+components)==1 else None
                if name=='setClassName' and strings:
                    target=strings[-1].replace('.','/') if not strings[-1].startswith('.') else ((strings[0]+strings[-1]).replace('.','/') if len(strings)==2 else None)
                receiver['target']=target;last=receiver
            elif owner=='android/content/ComponentName' and name=='<init>' and rr:
                classes=[v['value'] for v in values[1:] if v and v.get('kind')=='class']
                regs[rr[0]]={'kind':'component','target':classes[0] if len(classes)==1 else None}
            elif owner=='android/content/Intent' and receiver and sig.endswith('Landroid/content/Intent;'):
                last=receiver
            elif sig.endswith('Landroid/content/Intent;'):
                last={'kind':'factory','method':mid}
            activity_result=(name=='launch' and owner.startswith('androidx/activity/result/') and 'Ljava/lang/Object;' in sig)
            if (name in STARTS and 'Landroid/content/Intent;' in sig) or activity_result:
                params=re.findall(r'\[*L[^;]+;|\[*[ZBCSIJFD]',sig[1:sig.index(')')]);slot=0 if op.startswith('invoke-static') else 1;expr=None
                for param in params:
                    if (param=='Landroid/content/Intent;' or activity_result and param=='Ljava/lang/Object;') and slot<len(rr):expr=copy.deepcopy(regs.get(rr[slot]))
                    slot+=2 if param in {'J','D'} else 1
                rows.append(dict(kind='start',api=mid,intent=expr,dispatch_kind='activity-result-bridge' if activity_result else 'startActivity-family',**loc))
            if name in FINISH:finish.append(loc)
        else:
            m=re.match(r'const-class (v\d+), L([^;]+);',text)
            s=re.match(r'const-string(?:/jumbo)? (v\d+), "(.*)" //',text)
            obj=re.match(r'new-instance (v\d+), L([^;]+);',text)
            mv=re.match(r'move-object(?:/\w+)? (v\d+), (v\d+)',text)
            mr=re.match(r'move-result-object (v\d+)',text)
            ret=re.match(r'return-object (v\d+)',text)
            if m:regs[m[1]]={'kind':'class','value':m[2]};class_hints.append(dict(class_name=m[2],**loc))
            elif s:regs[s[1]]={'kind':'string','value':s[2]}
            elif obj:regs[obj[1]]={'kind':'intent','target':None} if obj[2]=='android/content/Intent' else {'kind':'object','class':obj[2]}
            elif mv:
                value=regs.get(mv[2]);regs.pop(mv[1],None)
                if value:regs[mv[1]]=value
            elif mr:
                regs.pop(mr[1],None)
                if last:regs[mr[1]]=last
                last=None
            elif ret and method.endswith('Landroid/content/Intent;'):returns.append(copy.deepcopy(regs.get(ret[1])))
            elif not text.startswith(('if-','goto','return','iput','sput','aput','monitor-','check-cast','nop')):
                dest=re.match(r'[^ ]+ (v\d+)',text)
                if dest:regs.pop(dest[1],None)
        if text.startswith(('if-','goto','return','throw','move-exception')) or 'switch ' in text:regs={};last=None
    if returns:rows.append(dict(kind='factory',method=method,dex=dex,returns=returns))
    for row in rows:
        if row['kind']=='start':
            row['finish_calls_same_method']=finish
            row['class_hints_same_method']=class_hints
            start=int(row['offset'],16)
            row['finish_lexical_order']='after_start' if any(int(x['offset'],16)>start for x in finish) else 'before_start' if finish else 'not_in_method'
    return rows

def resolve_intent(expr,factories,trail=()):
    if not expr:return [],'unknown'
    if expr.get('kind')=='intent':return ([expr['target']],'explicit-class') if expr.get('target') else ([], 'unknown')
    if expr.get('kind')=='factory':
        mid=expr['method']
        if mid in trail or len(trail)>=6:return [],'unknown'
        returns=factories.get(mid,[])
        resolved=[resolve_intent(x,factories,trail+(mid,)) for x in returns]
        targets=sorted({t for ts,_ in resolved for t in ts})
        if targets and all(ts for ts,_ in resolved):return targets,'local-factory-conditional'
    return [],'unknown'

CALIBRATION={
 'fd-gallery':('screen_likely','own gallery page; requires CE runtime already present'),
 'vlc':('screen_likely','own player/browser page; requires CE runtime already present'),
 'fd-tusky':('screen_likely','own login/onboarding or timeline page'),
 'fd-binaryeye':('screen_likely','CameraActivity page; camera functionality is separate'),
 'fd-filemanager':('screen_likely','own file manager page'),
 'wikipedia':('screen_likely','InitialOnboardingActivity welcome page only; stable article/content is not predicted')}

def classify(key,calls,status):
    if status!='scanned':return dict(tier='unknown',expected_advance='unknown',expected_page='unknown',reason='input identity or scan unavailable')
    if key=='termux':return dict(tier='no_permission_benefit_predicted',expected_advance='no',expected_page='no',reason='Disclosed negative control: second Activity already scheduled; first-frame/relayout wall remains')
    if key in CALIBRATION:return dict(tier=CALIBRATION[key][0],expected_advance='yes',expected_page='yes',reason='Calibration: observed permission denial before grant; '+CALIBRATION[key][1])
    strong=[x for x in calls if x['startup_reachable']=='yes-static' and x['non_launcher_targets']]
    specific=[x for x in strong if len(x.get('path',[]))<=4 and 'Landroid/content/Intent;' not in x['method'].split('(',1)[-1] and 'Ljava/lang/Object;' not in x['method'].split('(',1)[-1]]
    if specific:return dict(tier='advance_likely',expected_advance='yes',expected_page='unknown',reason='Explicit non-launcher target on conditional launcher lifecycle path; later walls and runtime background state unknown')
    if strong:return dict(tier='advance_possible',expected_advance='unknown',expected_page='unknown',reason='Explicit non-launcher target exists, but path is deep, input-Intent-dependent or a merged generic callback; fresh-launch branch is unproven')
    candidate=[x for x in calls if x['splash_class'] or x['startup_reachable']=='yes-static']
    if candidate:return dict(tier='candidate_unknown',expected_advance='unknown',expected_page='unknown',reason='Startup/Splash callsite found but destination or callback reachability is unresolved')
    return dict(tier='no_static_startup_hit',expected_advance='unknown',expected_page='unknown',reason='No bounded launcher startup witness; this does not prove absence of asynchronous, reflective or native navigation')
