#!/usr/bin/env python3
"""Conservative source table ownership. No filename-to-class or mere-string fallback."""
import collections, hashlib, json, re, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SLICE=Path('/Users/zhaoyue/orca/workspaces/01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-generation-source-slice-20260822-r1')
AOSP=SLICE/'aosp/frameworks/base'
DEFAULT_ROOTS=[ROOT/'bms/src/adapter/framework',
               AOSP/'core/jni',AOSP/'libs/hwui/jni',
               AOSP/'media/jni',AOSP/'opengl/jni']
# Source slices are attribution aids; compiled table matching is still mandatory.
TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_$][\w$]*|::|->|[^\s]')
COMMENTS=re.compile(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|(/\*.*?\*/|//[^\n]*)',re.S)

def strip_comments(text):
    return COMMENTS.sub(lambda m:m[1] if m[1] else ''.join('\n' if c=='\n' else ' ' for c in m[2]),text)

def balanced(tokens,start,opening='(',closing=')'):
    depth=0
    for i in range(start,len(tokens)):
        s=tokens[i][0]
        if s==opening:depth+=1
        elif s==closing:
            depth-=1
            if depth==0:return i
    return None

def split_args(tokens):
    out=[];begin=0;depth=0
    for i,t in enumerate(tokens):
        if t[0] in ['(','[','{']:depth+=1
        elif t[0] in [')',']','}']:depth-=1
        elif t[0]==',' and depth==0:out.append(tokens[begin:i]);begin=i+1
    out.append(tokens[begin:]);return out

def string_expr(tokens,constants):
    vals=[t[0] for t in tokens]
    if vals and all(v.startswith('"') for v in vals):
        try:return ''.join(json.loads(v) for v in vals)
        except (ValueError,TypeError):return None
    if len(vals)==1:
        items=constants.get(vals[0],set())
        if len(items)==1:return next(iter(items))
    return None

def parse_source(path,text=None):
    text=path.read_text(errors='replace') if text is None else text
    clean=strip_comments(text);ts=[(m[0],m.start()) for m in TOKEN.finditer(clean)]
    constants=collections.defaultdict(set)
    for i,t in enumerate(ts[:-2]):
        if re.fullmatch(r'[A-Za-z_$][\w$]*',t[0]) and ts[i+1][0]=='=':
            j=i+2
            while j<len(ts) and ts[j][0] not in [';',',','}']:j+=1
            value=string_expr(ts[i+2:j],constants)
            if value is not None:constants[t[0]].add(value)
    for m in re.finditer(r'^\s*#define\s+(\w+)\s+("[^"\n]+")\s*$',clean,re.M):
        constants[m[1]].add(json.loads(m[2]))
    # FindClass assignments are class objects, not string constants; use them only
    # when proving the owner of a RegisterNatives call below.
    class_vars=collections.defaultdict(set)
    calls=[]
    for i,t in enumerate(ts[:-1]):
        if ts[i+1][0]!='(' or not re.fullmatch(r'\w+',t[0]):continue
        end=balanced(ts,i+1)
        if end is None:continue
        args=split_args(ts[i+2:end])
        calls.append((i,t[0],args,end))
        if t[0] in {'FindClass','FindClassOrDie','findClassOrDie'}:
            cls=string_expr(args[-1],constants) if args else None
            before=ts[max(0,i-6):i]
            assign=next((j for j in range(len(before)-1,0,-1) if before[j][0]=='='),None)
            if cls and assign is not None:class_vars[before[assign-1][0]].add(cls)
    tables=[]
    for m in re.finditer(r'\bJNINativeMethod\s+(\w+)\s*\[\s*\]\s*=\s*\{',clean):
        start=next((i for i,t in enumerate(ts) if t[1]==m.end()-1),None)
        if start is None:continue  # quoted/generated source text is not a live table
        end=balanced(ts,start,'{','}')
        if end is None:continue
        tables.append({'name':m[1],'tokens':ts[start+1:end],'start':m.start(),'end':ts[end][1]})
    counts=collections.Counter(t['name'] for t in tables)
    owners=collections.defaultdict(list)
    for i,name,args,end in calls:
        if name in {'RegisterMethodsOrDie','registerNativeMethods','jniRegisterNativeMethods','RegisterNativeMethods'} and len(args)>=3:
            cls=string_expr(args[1],constants);table=args[2]
        elif name=='RegisterNatives' and len(args)>=2:
            cls=string_expr(args[0],class_vars);table=args[1]
        else:continue
        if cls and re.fullmatch(r'[A-Za-z_$][\w$]*(?:/[\w$]+)+',cls) and len(table)==1:
            owners[table[0][0]].append({'class':cls,'registration_line':text.count('\n',0,ts[i][1])+1,
                                       'registration':clean[ts[i][1]:ts[end][1]+1]})
    rows=[];unknown=[]
    for table in tables:
        registrations=owners[table['name']]
        classes={r['class'] for r in registrations}
        if not classes or counts[table['name']]!=1:
            unknown.append({'path':str(path),'table':table['name'],'line':text.count('\n',0,table['start'])+1,
                            'reason':'no unique explicit class registration','owners':registrations});continue
        for entry in split_args(table['tokens']):
            if not entry:continue
            method=sig=None;functions=[]
            if entry[0][0]=='{' and entry[-1][0]=='}':
                args=split_args(entry[1:-1])
                if len(args)==3:
                    method=string_expr(args[0],constants);sig=string_expr(args[1],constants)
                    expression=''.join(t[0] for t in args[2])
                    # Last identifier or qualified name after casts is the function reference.
                    match=re.search(r'([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\)*\s*$',expression)
                    if match:functions=[match[1]]
            elif len(entry)>2 and entry[1][0]=='(':
                macro=entry[0][0];end=balanced(entry,1)
                args=split_args(entry[2:end]) if end is not None else []
                # AOSP's explicit NATIVE_METHOD family joins class and method.
                if macro in {'NATIVE_METHOD','FAST_NATIVE_METHOD','CRITICAL_NATIVE_METHOD'} and len(args)==3:
                    if len(args[0])==len(args[1])==1:
                        method=args[1][0][0];sig=string_expr(args[2],constants)
                        functions=[args[0][0][0]+'_'+method]
            if not method or not sig or not re.fullmatch(r'\([^)]*\)[VZBCSIJFD\[L].*',sig) or not functions:
                unknown.append({'path':str(path),'table':table['name'],'line':text.count('\n',0,entry[0][1])+1,
                                'reason':'unsupported entry expression/macro; not guessed',
                                'text':clean[entry[0][1]:entry[-1][1]+len(entry[-1][0])]});continue
            for cls in sorted(classes):rows.append({'class':cls,'method':method,'signature':sig,'path':str(path),
                         'line':text.count('\n',0,entry[0][1])+1,'table':table['name'],
                         'function_names':functions,'function_tokens':[p for f in functions for p in f.split('::')],
                         'registration_evidence':[r for r in registrations if r['class']==cls],
                         'source_text':clean[entry[0][1]:entry[-1][1]+len(entry[-1][0])],
                         'attribution':'explicit-class-table-registration-v3'})
    return rows,unknown

def symbol_matches(source,symbols):
    # Itanium symbols embed length-prefixed identifiers; never match only the class
    # token (e.g. PaintGlue) while ignoring the function name.
    for qualified in source['function_names']:
        parts=qualified.split('::')
        for symbol in symbols:
            if symbol==qualified or symbol==parts[-1] and len(parts)==1:return True
            # Length prefixes disambiguate method names; scope and method must be adjacent.
            encoded=r'L?'.join(re.escape(str(len(p))+p) for p in parts)
            if symbol.startswith('_Z') and re.search(r'(?<![0-9])'+encoded+r'(?:E|[A-Za-z0-9_]|$)',symbol):return True
    return False

def source_tables(classes,roots=None):
    mapping=collections.defaultdict(list);inputs=[];unknown=[];paths=set()
    for root in roots or DEFAULT_ROOTS:
        if not root.exists():continue
        for p in root.rglob('*'):
            if p.is_file() and p.suffix in {'.cpp','.cc','.c','.h'}:paths.add(p)
    for p in sorted(paths):
        txt=p.read_text(errors='replace')
        if 'JNINativeMethod' not in txt:continue
        rows,miss=parse_source(p,txt)
        if rows or miss:
            inputs.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
            unknown+=miss
        for r in rows:
            if r['class'] in classes:mapping[(r['class'],r['method'],r['signature'])].append(r)
    return mapping,inputs,unknown

def main():
    rows,inputs,unknown=source_tables(set(),[])
    # CLI inventory is independent of declarations.
    inventory=[]
    for root in DEFAULT_ROOTS:
        if root.exists():
            for p in sorted(root.rglob('*.cpp')):
                parsed,_=parse_source(p);inventory+=parsed
    out=HERE/'v3/evidence';out.mkdir(parents=True,exist_ok=True)
    (out/'source-registration-inventory.json').write_text(json.dumps({'rows':inventory,'inputs':inputs,'unknown':unknown},indent=2)+'\n')
    print(len(inventory),'mapped source rows;',len(inputs),'source files;',len(unknown),'unresolved entries/tables')

if __name__=='__main__':main()
