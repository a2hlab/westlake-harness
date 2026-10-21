#!/usr/bin/env python3
"""Seal an explicit small landing list; exclude binaries and large raw outputs."""
from pathlib import Path
from inspect_inputs import sha,save
D=Path(__file__).resolve().parent;R=D.parents[2]
names=['README.md','documentation.json','prepare.py','inspect_inputs.py','precheck_candidate.py','prepare_recovery.py','run_checks.py','export_evidence.py','check_receipt.py','seal_delivery.py','acceptance-verification.json','assembly.json','baseline-319.json','recovery-binding.json','input-pins.json','abi-consumers.json','source-files.json','namespace-owners.json','current-abi-aliases.json','current-source-profiles.json','six-targets.json','transaction-plan.json','results.json','gates.json','gate-commands.json','findings.unsigned.json','package-index.json','evidence-index.json']
files=[D/n for n in names]+sorted((D/'first-slice-01').iterdir())+[R/'tools/spec-checks/tests/commercial_game_locale_transaction_package.rs']
if (D/'validation.json').exists():files.append(D/'validation.json')
rows=[{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files];save(D/'manifest.json',{'schema':'g32-small-delivery/v1','files':rows})
(D/'landing-paths.txt').write_text('\n'.join([x['path'] for x in rows]+[str((D/'manifest.json').relative_to(R)),str((D/'landing-paths.txt').relative_to(R))])+'\n')
print({'files':len(rows)+2,'bytes':sum(x['bytes'] for x in rows)+(D/'manifest.json').stat().st_size+(D/'landing-paths.txt').stat().st_size,'manifest_sha256':sha(D/'manifest.json')})
