from pathlib import Path
import hashlib,json,re,shutil,sys
R=Path(__file__).resolve().parent;raw=Path(sys.argv[1]);out=R/'screens';out.mkdir(exist_ok=True)
for key in ['helloworld','wikipedia','zigzag']:
 src=raw/key;dst=R/key;dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.is_file() and (p.name in ['record.json','timeline.txt','processes-after.txt'] or p.name.endswith(('.sha256','.late-sha256','-maps.txt'))):shutil.copy2(p,dst/p.name)
 for shot in ['t3','final']:shutil.copy2(src/(shot+'.jpeg'),out/(key+'-'+shot+'.jpeg'))
 pids={int(re.search(r'child-proof-(\d+)',p.name).group(1)) for p in src.glob('child-proof-*.sha256')}
 lines=(src/'hilog.txt').read_text(errors='replace').splitlines()
 patterns=r'(SIGCHAIN|SIGSEGV|SIGBUS|special_handler|special handler|do_handle_signal|directly return|performCreate|finishActivity|System.exit|Terminat|LOAD_ERROR|FAIL_SEALED|CHILD_A02|onCreate|RuntimeInit|RsFrameReportExt)'
 selected=[f'{i}: {line}' for i,line in enumerate(lines,1) if any(re.search(r'\s'+str(pid)+r'\s',line) for pid in pids) and re.search(patterns,line)]
 (dst/'hilog-excerpt.txt').write_text('\n'.join(selected)+'\n')
 (dst/'provenance.json').write_text(json.dumps({'raw_directory':str(src),'pids':sorted(pids),'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in src.iterdir() if p.is_file()}},indent=2)+'\n')
for n in ['identity-before.txt','identity-after.txt','shell-mountinfo.txt']:shutil.copy2(raw/n,R/n)
p=R/'results.json';d=json.loads(p.read_text());d['observations']={}
for key in ['helloworld','wikipedia','zigzag']:
 rec=json.loads((raw/key/'record.json').read_text());d['observations'][key]={'pids_after':rec['pids_after'],'new_faults':rec['new_faults'],'screenshot':'screens/'+key+'-final.jpeg','inner_visual':'own interface' if key!='wikipedia' else 'desktop','outer_visual':'pending review'}
d['raw_run']=str(raw);d['package_manifest_sha256']=hashlib.sha256((R/'package-manifest.json').read_bytes()).hexdigest();p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
