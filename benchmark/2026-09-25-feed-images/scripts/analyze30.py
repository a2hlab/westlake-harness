"""Read archived evidence only; never contacts the board."""
import collections, gzip, hashlib, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
def read(rel):
 p=E/rel
 if p.exists(): return p.read_bytes()
 return gzip.decompress((E/(rel+'.gz')).read_bytes())
results=[]
for p in sorted(E.glob('*/launch-config.json')):
 name=p.parent.name
 if name.startswith('control-'): continue
 lines=read(name+'/child.stderr').decode(errors='replace').splitlines()
 errors=[{'line':i,'text':s} for i,s in enumerate(lines,1) if '__ndk1' in s and 'symbol not found' in s]
 counter=collections.Counter()
 for row in errors:
  m=re.search(r'Error relocating .*?/(lib[^/ ]+\.so):',row['text'])
  counter[m[1] if m else 'unclassified']+=1
 signals=[{'line':i,'text':s} for i,s in enumerate(lines,1) if 'Fatal signal' in s]
 ui=[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[INITCHILD-FAIL]' in s]
 residual=[{'line':i,'text':s} for i,s in enumerate(lines,1) if 'symbol not found' in s and '__ndk1' not in s]
 controls=[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[SOURCE-CONTROL] command=' in s and 'command=v ' not in s]
 maps=read(name+'/maps.txt').decode(errors='replace') if (E/name/'maps.txt').exists() or (E/name/'maps.txt.gz').exists() else ''
 loaded=sorted(set(re.findall(r'/lib/arm64-v8a/(lib[^/\s]+\.so)',maps)))
 results.append({'run':name,'native_targets':json.loads(p.read_text())['native_targets'],'ndk1_symbol_not_found':len(errors),'errors_by_library':dict(counter),'first_errors':errors[:2],'other_symbol_not_found':residual,'fatal_signals':signals,'ui_failure_lines':ui,'fault_files':read(name+'/fault-paths.txt').decode().splitlines(),'input_commands':controls,'article_launch_lines':[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[WESTLAKE-DL2] in-process launch of com.ss.android.detail.feature.detail2.view.NewDetailActivity' in s],'touch_events':[{'line':i,'text':s} for i,s in enumerate(lines,1) if '[TOUCH21]' in s],'mapped_apk_libraries':loaded})
faults=[]
for run in ['full-2','full-3','baseline-3']:
 for p in sorted((E/run).glob('cppcrash-*')):
  text=(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()).decode(errors='replace')
  pc=int(re.search(r' pc:([0-9a-f]+)',text)[1],16)
  mapped=None
  for m in re.finditer(r'^([0-9a-f]+)-([0-9a-f]+) ([-rwxps]+) ([0-9a-f]+) (.+)$',text,re.M):
   lo,hi,offset=int(m[1],16),int(m[2],16),int(m[4],16)
   if lo<=pc<hi:
    mapped={'library':m[5],'pc':hex(pc),'mapping_start':hex(lo),'mapping_offset':hex(offset),'file_offset':hex(pc-lo+offset)};break
  faults.append({'run':run,'file':str(p.relative_to(E)),'reason':re.search(r'^Reason:(.+)$',text,re.M)[1],'fault_thread':re.search(r'^Tid:(.+)$',text,re.M)[1],'pc_mapping':mapped})
result={'runs':results,'native_faults':faults,'controls':[json.loads(p.read_text()) for p in sorted(E.glob('control-*/control-result.json'))]}
for control in result['controls']:
 lines=read('control-'+control['app']+'/child.stderr').decode(errors='replace').splitlines()
 control['null_pointer_exceptions']=[{'line':i,'text':s} for i,s in enumerate(lines,1) if 'NullPointerException' in s]
result['status']='blocked'
result['R2']='partially'
result['blocker']='Readable article page not demonstrated: baseline-3 and full-3 both launch NewDetailActivity then crash in WebView RenderThread at file offset 0x1e006f0. full-2 also has a distinct ICU/free failure; cause not established.'
(ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print([(x['run'],x['ndk1_symbol_not_found'],len(x['fault_files'])) for x in results])
