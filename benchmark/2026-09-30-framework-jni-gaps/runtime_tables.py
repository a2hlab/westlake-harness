"""Attribute ART/libcore tables as runtime-owned, never offer them as app gapfill stubs."""
import collections,gzip,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-09-29-static-wall-prediction'))
import registration_sources as rs
from scan_jni import ELF,sha
from westlake import normalize_tables
AOSP=rs.SLICE/'aosp'
ROOTS=[AOSP/'art/runtime/native',AOSP/'libcore/luni/src/main/native']

def main():
    inv=json.load(gzip.open(HERE/'evidence/native-inventory.json.gz','rt'))
    sources=collections.defaultdict(list);inputs=[]
    for root in ROOTS:
      for p in sorted(root.glob('*')):
        if p.suffix not in {'.cc','.cpp','.h'}:continue
        text=p.read_text(errors='replace')
        if 'JNINativeMethod' not in text:continue
        # native_util.h:40-41 proves this exact gMethods expansion.
        text=re.sub(r'REGISTER_NATIVE_METHODS\(("[^"\n]+")\)',r'jniRegisterNativeMethods(env,\1,gMethods,0)',text)
        rows,_=rs.parse_source(p,normalize_tables(text))
        if rows:inputs.append({'path':str(p),'sha256':sha(p)})
        for row in rows:sources[row['class']+'.'+row['method']+row['signature']].append(row)
    libfiles={}
    for inp in inv['inputs']:
      p=Path(inp['path'])
      if p.suffix=='.so' and inp['sha256'] not in libfiles:
        elf=ELF(p);libfiles[inp['sha256']]={'path':str(p),'compiled_sources':{s['name'] for s in elf.symbols if s['type']==4}}
    bypath={l['path']:l for l in libfiles.values()}
    matches={}
    for m in inv['methods']:
      if m['status']!='unknown':continue
      proof=[]
      for table in m['evidence']:
        lib=bypath.get(table['library'])
        if not lib:continue
        for src in sources.get(m['id'],[]):
          if Path(src['path']).name in lib['compiled_sources'] and rs.symbol_matches(src,table['function_symbols']):
            proof.append({'compiled_table':table,'source':src})
      if proof:matches[m['id']]=proof
    with gzip.open(HERE/'evidence/runtime-tables.json.gz','wt') as f:json.dump({'sources':sources,'inputs':inputs,'compiled_matches':matches,'macro_evidence':str(AOSP/'art/runtime/native/native_util.h')+':40'},f)
    print('ART/libcore source methods',len(sources),'new compiled matches',len(matches),flush=True)
if __name__=='__main__':main()
