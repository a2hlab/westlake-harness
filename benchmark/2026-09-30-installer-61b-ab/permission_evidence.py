# Copied unchanged from cx-bms compare.py, commit 36529f13.
# Source SHA256 b13b51f9b51fa81921eb150a2f31dd823f8cea659afb08d92152a07327e46249
import re,json,hashlib
from pathlib import Path
PID=re.compile(r'^\S+ \S+\s+(\d+)\s+\d+ ')
TRACE=re.compile(r'\[([0-9a-f]{12,})(?:,|\])')
CLUE=re.compile(r'main_threw|FATAL EXCEPTION|Caused by:|Unable to (?:start|resume)|dlopen_ns failed|Error relocating|Error loading shared library|No implementation found|StartAbility returned|EGL_NO_SURFACE|SIGABRT|SIGSEGV|\b(?:bind|attach) (?:FAILED|failed)|startActivity.*(?:component|cmp=)|\[B8-.*(?:FAIL|fail)',re.I)

def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def permission_state(path,name):
    if not path.exists():return 'unknown'
    try:
        text=path.read_text();b=json.loads(text[text.index('{'):]);names=b['reqPermissions'];states=b['reqPermissionStates']
        if not isinstance(names,list) or not isinstance(states,list):return 'unknown'
        if name not in names:return 'absent'
        i=names.index(name)
        if i>=len(states):return 'unknown'
        return 'granted' if states[i]==0 else 'not_granted'
    except (ValueError,KeyError,TypeError):return 'unknown'

def extract(record):
    r=json.loads(record.read_text());log=record.parent/'hilog.txt'
    result={'key':r['key'],'record':str(record),'record_sha256':sha(record),'log':str(log),'log_sha256':None,'target_pids':[],'clues':[],'startability_returns':[],'launch_requests':[],'background_trace_evidence':[],'background_denials':[],'scope':'exact bundle PID anchor; system denial additionally requires matching app-requested target and exact trace ID'}
    if not log.exists():return result
    result['log_sha256']=sha(log);lines=log.read_text(errors='replace').splitlines();pids=set()
    for line in lines:
        if 'nativeOnScheduleLaunchApplication ENTRY bundle='+str(r.get('package'))+' ' in line:
            m=PID.match(line)
            if m:pids.add(m[1])
    result['target_pids']=sorted(map(int,pids))
    targets=set()
    for n,line in enumerate(lines,1):
        m=PID.match(line)
        if m and m[1] in pids:
            call=re.search(r'nativeStartAbility: bundle=([^,]+), ability=([^,]+)',line)
            if call and call[1]==r.get('package'):
                targets.add(call[2]);result['launch_requests'].append({'line':n,'pid':int(m[1]),'target':call[2],'text':line})
    traces=set()
    for n,line in enumerate(lines,1):
        trace=TRACE.search(line)
        if trace and 'NotifySCBPendingActivation' in line and any(re.search(r'target:\s*'+re.escape(t)+r'(?:requestId|\s|$)',line) for t in targets):
            traces.add(trace[1]);result['background_trace_evidence'].append({'line':n,'trace':trace[1],'text':line})
    for n,line in enumerate(lines,1):
        trace=TRACE.search(line)
        if trace and trace[1] in traces and ('DisallowActivationFromPendingBackground' in line or ('permission_verification' in line and 'BACKGROUND' in line)):
            item={'line':n,'trace':trace[1],'text':line};result['background_trace_evidence'].append(item)
            if 'no permission to start ability from Background' in line:result['background_denials'].append(item)
    for n,line in enumerate(lines,1):
        m=PID.match(line)
        if not m or m[1] not in pids or not CLUE.search(line):continue
        result['clues'].append({'line':n,'pid':int(m[1]),'text':line})
        code=re.search(r'StartAbility returned\s+(-?\d+)',line)
        if code:result['startability_returns'].append({'code':int(code[1]),'line':n,'pid':int(m[1])})
    return result
