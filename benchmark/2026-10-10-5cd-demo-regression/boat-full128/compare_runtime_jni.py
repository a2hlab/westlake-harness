#!/usr/bin/env python3
"""Offline comparison of the exact Boat and U13 ELFs; no board/build commands.
Uses the repository's relocation-aware JNI scanner. Same-name tables are scoped
by their ELF STT_FILE owner, preventing other classes' nativeDispose etc. from
being mistaken for replacement coverage. Source-file ownership is not itself
proof of the class passed to RegisterNatives; source excerpts accompany it.
"""
import argparse,collections,hashlib,importlib.util,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXPECTED={'u13':'18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae','boat':'adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owned_tables(e):
 objects=[];owner=None
 for sym in e.symbols:
  if sym['type']==4:owner=sym['name']
  if sym['type']==1 and sym['size']:objects.append((sym,owner))
 rows=[]
 for row in e.tables():
  addr=int(row['table_address'],16)
  found=[(s,f) for s,f in objects if s['value']<=addr and addr+24<=s['value']+s['size']]
  if found:
   obj,fil=min(found,key=lambda x:x[0]['size']);row.update(elf_source_file=fil,elf_table_symbol=obj['name'])
  rows.append(row)
 return rows

def compare(scan,paths):
 elfs={k:scan.ELF(v) for k,v in paths.items()};tables={k:owned_tables(e) for k,e in elfs.items()}
 key=lambda r:(r.get('elf_source_file'),r.get('elf_table_symbol'),r['method'],r['signature'])
 boat_keys={key(r) for r in tables['boat']}
 scoped=[r for r in tables['u13'] if r.get('elf_source_file') and key(r) not in boat_keys]
 global_keys={(r['method'],r['signature']) for r in tables['boat']}
 global_delta=[r for r in tables['u13'] if (r['method'],r['signature']) not in global_keys]
 regs=[];bsyms={s['name']:s for s in elfs['boat'].symbols if s['section']}
 for sym in elfs['u13'].symbols:
  name=sym['name'];other=bsyms.get(name)
  if sym['section'] and sym['type']==2 and any(x in name for x in ('register_android_', 'register_com_', 'register_westlake_', 'register_n2_', 'register_n10b_', 'n2_register_')) and (not other or (sym['bind']==1 and other['bind']!=1)):
   row={'symbol':name,'u13':sym,'boat':other}
   if other:
    body=elfs['boat'].at(other['value'],other['size']).hex();row.update(boat_body_hex=body,boat_is_return_zero_stub=body in ('00008052c0035fd6','000080d2c0035fd6','e0031f2ac0035fd6'))
   regs.append(row)
 return elfs,tables,scoped,global_delta,regs

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--u13',type=Path,required=True);ap.add_argument('--boat',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();paths={'u13':a.u13,'boat':a.boat}
 for k,p in paths.items():
  if sha(p)!=EXPECTED[k]:raise ValueError('exact artifact SHA mismatch: '+k)
 scanner=ROOT/'benchmark/2026-09-29-static-wall-prediction/scan_jni.py';s=importlib.util.spec_from_file_location('jni_scanner',scanner);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 elfs,tables,scoped,global_delta,regs=compare(m,paths);a.out.mkdir(parents=True,exist_ok=True)
 for tag,rows in tables.items():(a.out/(tag+'-owned-tables.json')).write_text(json.dumps(rows,indent=2)+'\n')
 (a.out/'scoped-table-delta.json').write_text(json.dumps(scoped,indent=2)+'\n')
 (a.out/'u13-only-table-entries.json').write_text(json.dumps(global_delta,indent=2)+'\n')
 counts=collections.Counter(r['elf_source_file'] for r in scoped)
 result={'artifacts':{k:{'sha256':sha(p),'bytes':p.stat().st_size} for k,p in paths.items()},'scanner_sha256':sha(scanner),'table_counts':{k:len(v) for k,v in tables.items()},'export_counts':{k:len(e.exports) for k,e in elfs.items()},'scoped_absent_table_rows':len(scoped),'scoped_by_translation_unit':dict(counts),'globally_absent_unique_name_descriptor_pairs':len({(r['method'],r['signature']) for r in global_delta}),'registrar_missing_or_weak':regs,'limitations':['ELF table scope is not a proof of runtime registration execution.','Other libraries might supply some methods; only these two artifacts were compared.','Stack/unnamed tables require separate source attribution; no class is inferred from a method name alone.']}
 (a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 # Known answers tied to the exact artifacts, not inferred from strings alone.
 assert len([r for r in regs if r.get('boat_is_return_zero_stub')])==4
 assert any(r['method']=='nativeOpen' and r['signature']=='(Ljava/lang/String;ILjava/lang/String;ZZII)J' for r in global_delta)
 assert counts['android_database_SQLiteConnection.cpp']==27
 assert counts['android_view_VelocityTracker.cpp']==7
 print(json.dumps({'known_answers':'4/4 PASS','u13_tables':len(tables['u13']),'boat_tables':len(tables['boat']),'scoped_missing':len(scoped),'global_unique_missing':result['globally_absent_unique_name_descriptor_pairs'],'groups':dict(counts)},indent=2))
if __name__=='__main__':main()
