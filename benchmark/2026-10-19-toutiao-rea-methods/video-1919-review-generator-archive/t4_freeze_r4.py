from pathlib import Path
import json,hashlib,subprocess
R=Path.cwd();B=Path('benchmark/2026-10-19-toutiao-rea-methods');P=B/'video-1919-r4-live-review';Q=B/'video-1919-r4-api-final';D=B/'video-1919-r4-final-packet';A=Path('benchmark/2026-10-19-api-progress-update');(R/D).mkdir(exist_ok=True)
h=lambda p:hashlib.sha256((R/p).read_bytes()).hexdigest()
def w(p,d):(R/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
files=sorted([str(f.relative_to(R)) for root in [R/P,R/Q] for f in root.rglob('*') if f.is_file()]+[str(A/n) for n in ['observations.json','observations.csv','index.html','results.json']])
proc=subprocess.run(['python3','scripts/lab/check_user_paths.py',*files],capture_output=True,text=True);assert proc.returncode==0,proc.stdout+proc.stderr
(R/D/'user-paths.stdout.txt').write_text(proc.stdout);(R/D/'user-paths.stderr.txt').write_text(proc.stderr)
# Verify evidence screenshots and scripts against pinned original bytes where copied unchanged.
source=json.loads((R/P/'source-pins.json').read_text())['files'];pins={x['sha256'] for x in source}
images=[f for f in (R/P).rglob('*.jpeg')];assert len(images)==12;assert all(hashlib.sha256(f.read_bytes()).hexdigest() in pins for f in images)
for f in (R/P/'historical-recipes').glob('*.py'):assert hashlib.sha256(f.read_bytes()).hexdigest() in pins
row=json.loads((R/A/'observations.json').read_text());assert len(row['rows'])==4
old=json.loads((R.parent/'westlake-harness'/A/'observations.json').read_text());assert row['rows'][:3]==old['rows']
(R/D/'ACK.md').write_text('''# video-1919-r4-final-packet\n\nACCEPT for evidence delivery, not playback acceptance. Three GOT slots matched; three25-second groups remain cover-only. Audio/full loading unknown. Two candidate navigation attempts did not return to feed. Original unknown got receipts and all12 actual screenshots preserved.\n\nFour-file rollback and fresh-boot feed verified; MAIN UNLOCK20:28:45 read. Archive14,884,299B SHA5247bf079bcbc4d5ccb4ac0ac36b880b6bef86e270fb4ba8a7bd5667d069c987 bound to outer verified receipt. API has4 rows/51 exact references (10+10+12+19); first3 unchanged and historical315 untouched. Original renderer rc0; public path gate rc0. No device calls/builds/push.\n\n'''+(R/P/'facts.txt').read_text()+'\nStandard alive unknown is not a process-death verdict. Source checks and raw stat observations are reported separately. Exact landing-paths and SHA256SUMS accompany this delivery; freeze.json binds both without a hash cycle.\n')
w(D/'checks.json',{'token':'video-1919-r4-final-packet','user_paths_rc':proc.returncode,'images':12,'images_match_original_pins':True,'actual_script_bytes_match_original_pins':True,'api_rows':4,'api_references':51,'api_first_three_unchanged':True,'historical315_modified':False,'renderer_rc':0,'device_calls':0,'builds':0,'scope':'Evidence verification only; no runtime regression rerun.'})
files+= [str(D/n) for n in ['ACK.md','checks.json','user-paths.stdout.txt','user-paths.stderr.txt']];files=sorted(files)
(R/D/'SHA256SUMS').write_text(''.join(h(Path(f))+'  '+f+'\n' for f in files))
listing=sorted(files+[str(D/n) for n in ['SHA256SUMS','landing-paths.txt','freeze.json']]);(R/D/'landing-paths.txt').write_text('\n'.join(listing)+'\n')
w(D/'freeze.json',{'token':'video-1919-r4-final-packet','status':'FROZEN_EVIDENCE_PLAYBACK_NOT_PASSED','landing_files':len(listing),'hashed_payload_files':len(files),'sha256sums':{'path':str(D/'SHA256SUMS'),'sha256':h(D/'SHA256SUMS')},'landing':{'path':str(D/'landing-paths.txt'),'sha256':h(D/'landing-paths.txt')},'control_exclusion':'SHA256SUMS excludes itself, landing-paths.txt and freeze.json to avoid recursive hashes. freeze.json binds sums and landing; its hash is supplied in handoff.','archive_sha256':'5247bf079bcbc4d5ccb4ac0ac36b880b6bef86e270fb4ba8a7bd5667d069c987','api_references_by_row':[10,10,12,19],'api_references_total':51,'previous_rows_unchanged':True})
for line in (R/D/'SHA256SUMS').read_text().splitlines():
 expected,f=line.split('  ',1);assert h(Path(f))==expected
print(json.dumps({'landing_files':len(listing),'sha256sums':h(D/'SHA256SUMS'),'landing_sha256':h(D/'landing-paths.txt'),'freeze_sha256':h(D/'freeze.json'),'api_observations_sha256':h(A/'observations.json'),'packet_dir':str(R/D),'path_gate':proc.stdout.strip()},indent=2))
