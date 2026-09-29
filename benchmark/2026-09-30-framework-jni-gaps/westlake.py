"""Exact JNI table/export copy candidates in read-only Westlake snapshots."""
import collections,gzip,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-09-29-static-wall-prediction'))
import registration_sources as rs
from scan_jni import jni_escape
ROOTS=[Path('/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/framework'),Path('/Users/zhaoyue/orca/workspaces/01.OH61AOSP16/real-work/src/adapter/framework')]

def scalar_tables(text):
    # A single JNINativeMethod passed by address is the same table contract.
    pattern=r'\bJNINativeMethod\s+(\w+)\s*=\s*\{([^{}]+)\}'
    names=[]
    def repl(m):
      names.append(m[1]);return 'JNINativeMethod '+m[1]+'[] = {{'+m[2]+'}}'
    text=re.sub(pattern,repl,text)
    for name in names:text=re.sub(r'&\s*'+re.escape(name)+r'\b',name,text)
    return text

def normalize_tables(text):
    text=scalar_tables(text)
    # C++ const_cast<char*>(literal) has exactly the same string value.
    text=re.sub(r'const_cast\s*<\s*char\s*\*\s*>\s*\(\s*("(?:\\.|[^"\\])*")\s*\)',r'\1',text)
    clean=rs.strip_comments(text)
    tokens=[(m[0],m.start(),m.end()) for m in rs.TOKEN.finditer(clean)]
    enclosing={};ends={};stack=[]
    for token,start,end in tokens:
      enclosing[start]=stack[-1] if stack else None
      if token=='{':stack.append(start)
      elif token=='}' and stack:ends[stack.pop()]=end
    replacements=[]
    for serial,m in enumerate(re.finditer(r'\bJNINativeMethod\s+(\w+)\s*\[\s*\]',clean)):
      scope=enclosing.get(m.start());end=ends.get(scope,len(text))
      name=m[1];new=name+'_gap_table_'+str(serial)
      for token,start,stop in tokens:
        if m.start(1)<=start<end and token==name:replacements.append((start,stop,new))
    for start,end,value in sorted(set(replacements),reverse=True):text=text[:start]+value+text[end:]
    return text

def definition(text,name):
    clean=rs.strip_comments(text);simple=name.split('::')[-1]
    pattern=r'(?<![\w])'+re.escape(simple)+r'\s*\([^;{}]{0,2000}\)\s*(?:const\s*)?\{'
    m=re.search(pattern,clean)
    if not m:return None
    depth=1;i=m.end()
    while i<len(clean) and depth:
      if clean[i]=='{':depth+=1
      elif clean[i]=='}':depth-=1
      i+=1
    body=clean[m.end():i-1].strip()
    neutral=not body or bool(re.fullmatch(r'return\s+(?:[\w.+-]+|static_cast<\w+>\([\w.+-]+\))\s*;',body))
    return {'function':name,'definition_line':text.count('\n',0,m.start())+1,'body_kind':'literal_return_or_empty_stub' if neutral else 'source_body_present','body_excerpt':text[m.start():i][:1000]}

def main():
    inv=json.load(gzip.open(HERE/'evidence/native-inventory.json.gz','rt'))
    methods={m['id']:m for m in inv['methods']};exports=collections.defaultdict(list)
    for mid,m in methods.items():
      short='Java_'+jni_escape(m['class'])+'_'+jni_escape(m['method'])
      long=short+'__'+jni_escape(m['signature'][1:m['signature'].index(')')])
      exports[short].append(mid);exports[long].append(mid)
    found=collections.defaultdict(list);inputs=[];unknown=[]
    for root in ROOTS:
      for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix not in {'.cpp','.cc','.c','.h'}:continue
        text=path.read_text(errors='replace')
        if 'JNINativeMethod' not in text and 'Java_' not in text:continue
        rows,miss=rs.parse_source(path,scalar_tables(text));unknown.extend(miss)
        normalized,extra_miss=rs.parse_source(path,normalize_tables(text))
        known={(r['class'],r['method'],r['signature'],r['line']) for r in rows}
        rows += [r for r in normalized if (r['class'],r['method'],r['signature'],r['line']) not in known]
        relevant=False
        for row in rows:
          mid=row['class']+'.'+row['method']+row['signature']
          if mid not in methods:continue
          bodies=[d for fn in row['function_names'] if (d:=definition(text,fn))]
          found[mid].append({**row,'basis':'exact_class_descriptor_registration_source','bodies':bodies,
                            'implementation':'body_found' if bodies else 'table_only_body_unresolved'})
          relevant=True
        for name in set(re.findall(r'\bJava_[A-Za-z0-9_]+',text)):
          mids=exports.get(name,[])
          if len(mids)!=1:continue
          body=definition(text,name)
          if not body:continue
          found[mids[0]].append({'path':str(path),'line':body['definition_line'],'function_names':[name],
                              'bodies':[body],'basis':'unique_declaration_JNI_export_source','implementation':'body_found'})
          relevant=True
        if relevant:inputs.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    with gzip.open(HERE/'evidence/westlake-sources.json.gz','wt') as f:json.dump({'roots':[str(p) for p in ROOTS],'inputs':inputs,'methods':found,'unresolved_tables':unknown},f)
    print('source-attributed methods',len(found),'body found',sum(any(x['bodies'] for x in rows) for rows in found.values()),flush=True)
if __name__=='__main__':main()
