#!/usr/bin/env python3
"""Seal only this offline evidence packet and the four rendered additive views."""
from pathlib import Path
import hashlib,json,subprocess
F=Path(__file__).resolve().parent;R=next(p for p in F.parents if (p/'scripts/lab/run_facts.py').is_file());P=F.parent/'video-1919-r6-live-review';A=R/'benchmark/2026-10-19-api-progress-update'
assert not (F/'freeze.json').exists(),'already frozen'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=json.loads((F/'checks.json').read_text());assert checks['first_five_objects_unchanged'] and checks['csv_all_fields_equal'] and checks['all_links_resolved']
(F/'README.md').write_text('''# R6 closed evidence packet\n\nScope: native diagnostic observation and verified restoration, not playback acceptance. See ../video-1919-r6-live-review/results.json for the final bounded verdict and facts.txt for actual counts. Four unchanged r4 artifacts; actual child property read true; three byte-identical cover screenshots; no audio or prepare-callback proof. Explicit r2 final guardian repairs the evidence linkage after helper r1 reads without deleting those errors. Baseline bytes/parameter106/same-plan state and actual second-icon feed are restored; canonical unlock22:03:56.\n\nThe raw remote archive is SHA/size verified in live-review/archive/window-archive.json. Public paths use HW248_ARTIFACT_ROOT; private originals remain byte-preserved. assemble.py and review_after_play.py preserve useful offline review code; no device calls are made by them. Historical execution scripts are not generic rerun tools. Source/build prerequisites are reused by exact references, not relabelled as new builds. Earlier intermediate checkpoints in live-review remain historical; results.json is authoritative.\n\nThe API successor adds exactly one observation. Original renderer validates all references, six-row CSV and links; prior five objects are equal to MAIN input and historical315 is not changed. Collect only landing-paths.txt. No push or staging was attempted.\n''')
facts=(P/'facts.txt').read_text();total=next(x for x in facts.splitlines() if x.startswith('TOTAL'))
(F/'ACK.md').write_text('''# ACK video-1919-r6-final-packet\n\nScoped ACCEPT of evidence/restoration; P1 NOT_PASSED_STATIC_COVER and audio UNKNOWN. Child bridge property read true observed; exact JNI caller not runtime-stack-proven. Restored firstchild7578 exit and erroneous r1 helper reads retained, explicit r2 child15451/105141 + actual feed closes restoration. UNLOCK22:03:56. Zero device/build calls.\n\nFacts (verbatim; alive_unknown is not a failure count):\n\n```text\n'''+total+'\n```\n\nAPI: 6 observations, 88 exact references (new row20), 91 HTML links; CSV all fields equal; previous five objects unchanged; historical315 unchanged.\n')
# Enumerate actual files (not directory names) for the path checker.
api=[A/n for n in ['observations.json','observations.csv','index.html','results.json']]
files=sorted(set([x for base in [F,P] for x in base.rglob('*') if x.is_file()]+api))
run=subprocess.run(['python3',str(R/'scripts/lab/check_user_paths.py'),*[str(x.relative_to(R)) for x in files]],capture_output=True,text=True)
(F/'path-gate.stdout.txt').write_text(run.stdout);(F/'path-gate.stderr.txt').write_text(run.stderr);assert run.returncode==0,run.stdout
(F/'path-gate.json').write_text(json.dumps({'rc':run.returncode,'exact_file_arguments':len(files),'tool_sha256':h(R/'scripts/lab/check_user_paths.py'),'directory_argument_check_not_used_for_acceptance':True},indent=2)+'\n')
files=sorted(set([x for base in [F,P] for x in base.rglob('*') if x.is_file()]+api))
excluded={'freeze.json','SHA256SUMS','landing-paths.txt'}
payload=[x for x in files if not (x.parent==F and x.name in excluded)]
manifest={'token':'video-1919-r6-final-packet','scope':'evidence and restoration only; no playback PASS','payload_count':len(payload),'files':[{'path':str(x.relative_to(R)),'sha256':h(x),'bytes':x.stat().st_size} for x in payload]}
(F/'freeze.json').write_text(json.dumps(manifest,indent=2)+'\n')
(F/'SHA256SUMS').write_text(''.join(h(x)+'  '+str(x.relative_to(R))+'\n' for x in payload+[F/'freeze.json']))
(F/'landing-paths.txt').write_text(''.join(str(x.relative_to(R))+'\n' for x in sorted(payload+[F/'freeze.json',F/'SHA256SUMS',F/'landing-paths.txt'])))
for row in manifest['files']:assert h(R/row['path'])==row['sha256']
print('FROZEN',len(payload)+3,'landing',len(payload),'payload','freeze',h(F/'freeze.json'));print(run.stdout.strip());print(total)
