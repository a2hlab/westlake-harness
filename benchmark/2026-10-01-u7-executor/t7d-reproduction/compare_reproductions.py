#!/usr/bin/env python3
"""Read-only comparison of T7d and three independent outputs; never promote."""
import argparse,hashlib,itertools,json,struct
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compare(paths,reference):
    names=list(reference['outputs']);results={}
    for label,root in paths.items():
        results[label]={n:sha(root/n) for n in names}
    pairs=[]
    for x,y in itertools.combinations(paths,2):
        different=[n for n in names if results[x][n]!=results[y][n]]
        a=(paths[x]/'boot.art').read_bytes();b=(paths[y]/'boot.art').read_bytes()
        offsets=[i for i in range(min(len(a),len(b))) if a[i]!=b[i]]
        pairs.append(dict(left=x,right=y,different_files=different,different_bytes=len(offsets),offsets=offsets,
                          same_size=len(a)==len(b),only_backtrace_field=len(a)==len(b) and all(0x3e3b8<=i<0x3e3c0 for i in offsets)))
    ranges=[]
    for n in names:
        if not n.endswith('.art'):continue
        data=(paths['T7d']/n).read_bytes()
        if data[:8]!=b'art\n108\x00':raise ValueError('unexpected image version')
        base,size=struct.unpack_from('<II',data,16)
        off,length=struct.unpack_from('<II',data,72+2*8)
        ranges.append(dict(file=n,image_begin=hex(base),image_end=hex(base+size),
                           ArtMethods_begin=hex(base+off),ArtMethods_end=hex(base+off+length)))
    values={}
    for name,root in paths.items():
        value,dex_pc=struct.unpack_from('<QQ',(root/'boot.art').read_bytes(),0x3e3b8)
        values[name]=dict(method_word=hex(value),dex_pc=dex_pc,
            inside_image_ArtMethods=any(int(r['ArtMethods_begin'],16)<=value<int(r['ArtMethods_end'],16) for r in ranges),
            inside_any_image=any(int(r['image_begin'],16)<=value<int(r['image_end'],16) for r in ranges))
    narrow=all(set(p['different_files'])<= {'boot.art'} and p['only_backtrace_field'] for p in pairs)
    varied=len({values[n]['method_word'] for n in ['R1','R2','R3']})>1
    verdict='verified-with-exception' if narrow and varied else 'unknown'
    return dict(provenance=verdict,exception_approval='pending',deployable=False,hashes=results,
                pairs=pairs,method_words=values,image_ArtMethod_ranges=ranges,all_other_26_identical=narrow,
                independent_reproduction_values_differ=varied)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    c=json.loads((a.root/'config.json').read_text());paths={'T7d':Path(c['reference']['paths']['outputs'])}
    paths.update({k:a.root/v/'arm64' for k,v in [('R1','run'),('R2','run-r2'),('R3','run-r3')]})
    result=compare(paths,c['reference']);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
