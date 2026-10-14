#!/usr/bin/env python3
"""Decode type_list order and Java content hashes without changing either DEX."""
import argparse,json,struct
from pathlib import Path
from compare_dex import read_dex,sections,sha
def uleb(d,p):
 n=s=0
 while True:
  b=d[p];p+=1;n|=(b&127)<<s
  if b<128:return n,p
  s+=7;assert s<35
# DEX descriptors in this inventory are ASCII. Reject rather than pretend full MUTF8 support.
def strings(d):
 n,o=struct.unpack_from('<II',d,56);out=[]
 for i in range(n):
  q=struct.unpack_from('<I',d,o+4*i)[0];length,q=uleb(d,q);e=d.index(0,q);raw=d[q:e]
  out.append(raw.decode('ascii') if all(c<128 for c in raw) else None)
 return out
def lists(d):
 st=strings(d);n,o=struct.unpack_from('<II',d,64);types=[st[struct.unpack_from('<I',d,o+4*i)[0]] for i in range(n)]
 rows=[]
 for kind,count,start,end in sections(d):
  if kind!=0x1001:continue
  q=start
  for _ in range(count):
   n=struct.unpack_from('<I',d,q)[0];key=tuple(types[struct.unpack_from('<H',d,q+4+2*i)[0]] for i in range(n));assert None not in key
   h=1
   for text in key:
    x=0
    for c in text:x=(31*x+ord(c))&0xffffffff
    h=(31*h+x)&0xffffffff
   rows.append({'types':list(key),'offset':q,'java_list_hash':f'{h:08x}','bucket512':(h^(h>>16))&511});q=(q+4+2*n+3)&~3
 return rows
def compare(a,b):
 left,right=lists(a),lists(b);lk={tuple(x['types']):x for x in left};rk={tuple(x['types']):x for x in right};assert set(lk)==set(rk)
 swapped=[]
 for i,x in enumerate(left):
  for y in left[i+1:]:
   xx,yy=rk[tuple(x['types'])],rk[tuple(y['types'])]
   if xx['offset']>yy['offset']:swapped.append({'left':x,'right':y,'rebuilt_offsets':[xx['offset'],yy['offset']],'same_content_hash_bucket512':x['bucket512']==y['bucket512']})
 return {'historical_dex_sha256':sha(a),'rebuilt_dex_sha256':sha(b),'type_list_count':len(left),'bucket_capacity512':'inferred from ConcurrentHashMap default resizing at load factor .75; not an original execution receipt','inversions':swapped,'historical_type_lists':left,'rebuilt_type_lists':right,'does_not_prove_historical_exact_reproduction':True}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--historical',type=Path,required=True);p.add_argument('--rebuilt',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.write_text(json.dumps(compare(read_dex(a.historical),read_dex(a.rebuilt)),indent=2)+'\n')
if __name__=='__main__':main()
