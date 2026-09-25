from common30 import *
import hashlib
runs=[];base=json.loads((R/'baseline-1/device-report.json').read_text())['source_files']
wanted={k:v['sha256'] for k,v in base.items()}
for p in sorted(R.glob('*/device-report.json')):
 if p.parent.name.startswith('control-'):continue
 d=json.loads(p.read_text());actual={k:v['sha256'] for k,v in d['source_files'].items()}
 diff=[k for k in wanted.keys()|actual.keys() if wanted.get(k)!=actual.get(k)]
 runs.append({'run':p.parent.name,'source_file_count':len(actual),'differences_from_baseline':diff,'all_static_files_identical':not diff,'runtime':d['runtime']})
 assert not diff,(p,diff)
result={'baseline':'#14 integration lineage as deployed for #21/#25: out-touch21/wake + out-touch21 framework/boot; out-sp20/webview-candidate','runtime_source_commit':subprocess.check_output(['git','-C',str(A/'westlake-touch21'),'rev-parse','HEAD'],text=True).strip(),'framework_report':str(R.parent/'touch25/framework-wake/device-report.json'),'framework_report_sha256':hashlib.sha256((R.parent/'touch25/framework-wake/device-report.json').read_bytes()).hexdigest(),'runs':runs}
(R/'runtime-provenance.json').write_text(json.dumps(result,indent=2)+'\n');print([(x['run'],x['source_file_count'],x['all_static_files_identical']) for x in runs])
