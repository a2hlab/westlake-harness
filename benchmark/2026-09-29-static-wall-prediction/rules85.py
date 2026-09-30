"""Pure static rules. No application keys or observed outcomes are inputs."""
import re,struct
from scan_apps import INVOKE
FAMILIES=('window-type-flags','in-app-bindservice','velocitytracker-jni','native-bionic-header','sharedpreferences-null')
# WindowSessionAdapter.java:82-95, Android WindowManager.LayoutParams constants.
SUPPORTED_FLAGS=0x01000000|0x00000100|0x00010000|0x00800000|0x80000000|0x00000400|0x00000080|0x00080000|0x00200000|0x00400000
BIONIC=re.compile(r'^(?:__errno|__system_property_.*|__.*_chk|__open_2|__read_chk|__register_atfork|android_dlopen_ext|android_get_device_api_level|__loader_.*)$')

def inspect_method(method,dex,insns):
    rows=[];regs={};classes=[];targets=set()
    for _,_,text in insns:
        m=re.search(r'(?:, |goto(?:/\w+)? )([0-9a-f]+) //',text)
        if m:targets.add(m[1].lstrip('0') or '0')
    switch=any('switch ' in text for _,_,text in insns)
    for off,line,text in insns:
        if (off.lstrip('0') or '0') in targets:regs={}
        base={'method':method,'dex':dex,'offset':off,'line':line,'instruction':text}
        inv=INVOKE.search(text)
        if inv:
            op,args,owner,name,sig=inv.groups();rr=re.findall(r'v\d+',args)
            if '..' in args and len(rr)==2:rr=[f'v{i}' for i in range(int(rr[0][1:]),int(rr[1][1:])+1)]
            vals=[regs.get(r) for r in rr] if not switch else [None]*len(rr)
            is_static=op.startswith('invoke-static');argvals=vals if is_static else vals[1:]
            family=None;reason=None;strength='api-reference';extra={}
            if name in {'addFlags','setFlags','setType','setAttributes'} and owner.startswith(('android/view/','android/app/')):
                family='window-type-flags';value=argvals[0] if argvals else None;extra={'constant':value,'policy':'source-derived; actual r14 policy equivalence unverified'}
                if name in {'addFlags','setFlags'} and isinstance(value,int):
                    mask=argvals[1] if name=='setFlags' and len(argvals)>1 else 0xffffffff
                    if not isinstance(mask,int):reason='unknown flag mask'
                    else:
                        unsupported=(value&mask&0xffffffff)&~SUPPORTED_FLAGS
                        extra['unsupported_bits']=hex(unsupported)
                        if unsupported:strength='unsupported-source-policy-constant';reason='set bits outside source allowlist'
                        else:family=None
                elif name=='setType' and isinstance(value,int):
                    if value in {1,2,3}:family=None
                    else:strength='nondefault-window-type';reason='non-main type needs adapter mapping'
                else:reason='window attributes or argument unknown'
            elif owner=='android/view/WindowManager$LayoutParams' and name=='<init>':
                # Android constructors: type/flags[/format], width/height/type/flags/format,
                # or width/height/x/y/type/flags/format.
                layout={'(I)V':(0,None),'(II)V':(0,1),'(III)V':(0,1),'(IIIII)V':(2,3),'(IIIIIII)V':(4,5)}
                if sig in layout:
                    ti,fi=layout[sig];typ=argvals[ti] if ti<len(argvals) else None;flags=argvals[fi] if fi is not None and fi<len(argvals) else 0
                    extra={'constant_type':typ,'constant_flags':flags}
                    unsupported=(flags&0xffffffff)&~SUPPORTED_FLAGS if isinstance(flags,int) else None
                    if unsupported or not isinstance(typ,int) or typ not in {1,2,3} or not isinstance(flags,int):
                        family='window-type-flags';reason='LayoutParams constructor type/flags require adapter policy'
                        strength='unsupported-source-policy-constant' if unsupported else 'constructor-attributes'
                        extra['unsupported_bits']=hex(unsupported) if unsupported is not None else None
            elif name in {'bindService','bindServiceAsUser','bindIsolatedService'} and 'Landroid/content/Intent;' in sig:
                family='in-app-bindservice';reason='bindService contract; explicit target may be unavailable';extra={'class_constants_in_method_before_call':list(classes),'intent_target':'unknown'}
            elif owner=='android/view/VelocityTracker':
                family='velocitytracker-jni';reason='framework wrapper requires native VelocityTracker registration'
            elif name in {'getSharedPreferences','getPreferences','getDefaultSharedPreferences'} and ('Landroid/content/SharedPreferences;' in sig):
                family='sharedpreferences-null';reason='non-null SharedPreferences return required; runtime null not statically proven'
            elif owner=='android/content/SharedPreferences' or owner.startswith('android/content/SharedPreferences$'):
                family='sharedpreferences-null';reason='dereference requires non-null SharedPreferences or Editor receiver'
            if family:rows.append({**base,**extra,'family':family,'target':owner+'.'+name+sig,'strength':strength,'reason':reason})
            if owner in {'java/lang/System','java/lang/Runtime'} and name in {'load','loadLibrary','loadLibrary0','nativeLoad'}:
                strings=[v for v in argvals if isinstance(v,str)]
                rows.append({**base,'family':'native-load-call','library':strings[0] if len(strings)==1 else None,'reason':'Only local constant propagation; wrappers remain unknown'})
        field=re.search(r'iput(?:-\w+)? (v\d+), v\d+, Landroid/view/WindowManager\$LayoutParams;\.(type|flags):I',text)
        if field:
            value=regs.get(field[1]) if not switch else None;kind=field[2]
            interesting=not isinstance(value,int) or (value not in {1,2,3} if kind=='type' else ((value&0xffffffff)&~SUPPORTED_FLAGS)!=0)
            if interesting:rows.append({**base,'family':'window-type-flags','field':kind,'constant':value,'strength':'unsupported-source-policy-constant' if isinstance(value,int) and kind=='flags' else 'attribute-write','reason':'LayoutParams write; alias/branch/execution and actual policy are conditional'})
        c=re.match(r'const(?:/\w+)? (v\d+), #int (-?\d+)',text)
        string=re.match(r'const-string(?:/jumbo)? (v\d+), "(.*)" //',text)
        cls=re.match(r'const-class (v\d+), L([^;]+);',text)
        move=re.match(r'move(?:-object)?(?:/\w+)? (v\d+), (v\d+)',text)
        if c:regs[c[1]]=int(c[2])
        elif string:regs[string[1]]=string[2]
        elif cls:regs[cls[1]]=('class',cls[2]);classes.append(cls[2])
        elif move:
            value=regs.get(move[2]);regs.pop(move[1],None)
            if value is not None:regs[move[1]]=value
        elif not text.startswith(('invoke-','if-','goto','return','iput','sput','aput','monitor-','check-cast')):
            m=re.match(r'[^ ]+ (v\d+)',text)
            if m:regs.pop(m[1],None)
        if text.startswith(('if-','goto','return','throw','move-exception')) or 'switch ' in text:regs={}
    return rows

def elf_info(data):
    result={'header':'unknown','imports':[],'exports':[],'needed':[],'errors':[]}
    if data[:4]!=b'\x7fELF':return {**result,'header':'invalid-magic'}
    if len(data)<64:return {**result,'header':'truncated'}
    if data[4:6]!=b'\x02\x01':return {**result,'header':'wrong-class-or-endian-for-arm64'}
    try:
        h=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
        if h[2]!=183:return {**result,'header':'wrong-machine-for-arm64'}
        if h[1]!=3:return {**result,'header':'not-ET_DYN'}
        if h[10] and (h[9]<56 or h[5]+h[9]*h[10]>len(data)):return {**result,'header':'invalid-program-header-table'}
        for i in range(h[10]):
            ph=struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9])
            if ph[0]==1 and (ph[2]+ph[5]>len(data) or ph[5]>ph[6]):return {**result,'header':'invalid-load-segment'}
        result['header']='valid-ELF64-AArch64'
        if not h[12]:return {**result,'symbol_status':'unknown-no-section-table'}
        if h[11]<64 or h[6]+h[11]*h[12]>len(data):return {**result,'symbol_status':'unknown-invalid-section-table'}
        secs=[struct.unpack_from('<IIQQQQIIQQ',data,h[6]+i*h[11]) for i in range(h[12])]
        def string(s,idx):
            off=s[4]+idx
            if off>=len(data):raise ValueError('string offset')
            return data[off:data.index(b'\0',off)].decode(errors='replace')
        for section in secs:
            if section[1] not in {6,11}:continue
            st=secs[section[6]]
            if section[4]+section[5]>len(data):raise ValueError('section bounds')
            if section[1]==6:
                for off in range(section[4],section[4]+section[5],section[9] or 16):
                    tag,val=struct.unpack_from('<qQ',data,off)
                    if tag==1:result['needed'].append(string(st,val))
            else:
                for off in range(section[4],section[4]+section[5],section[9] or 24):
                    no,info,other,ndx,_,_=struct.unpack_from('<IBBHQQ',data,off)
                    if not no or info>>4 not in {1,2}:continue
                    name=string(st,no)
                    if not ndx:result['imports'].append({'name':name,'weak':info>>4==2})
                    elif other&3 in {0,3}:result['exports'].append(name)
        result['symbol_status']='parsed';return result
    except (ValueError,IndexError,struct.error) as exc:
        return {**result,'symbol_status':'unknown-malformed','errors':[str(exc)]}

def native_verdict(library,package_exports,app_exports):
    bad=library['header'] not in {'valid-ELF64-AArch64','unknown'}
    dependencies=[]
    for symbol in library['imports']:
        if BIONIC.match(symbol['name']):
            providers=package_exports.get(symbol['name'],[])
            dependencies.append({**symbol,'providers':providers,'app_provider':symbol['name'] in app_exports,
                'resolution':'weak-optional' if symbol['weak'] else 'definition-present-scope-unknown' if providers or symbol['name'] in app_exports else 'not-in-reviewed-export-set'})
    # Weak optional imports alone do not constitute a blocking static hit.
    strong=[s for s in dependencies if not s['weak']]
    return {'hit':bad or bool(strong),'header_invalid':bad,'bionic_imports':dependencies,
        'strong_unprovided':[s['name'] for s in strong if s['resolution']=='not-in-reviewed-export-set'],
        'runtime_dlopen_header':'unknown; valid input bytes do not prove the loader opens the same file or namespace'}
