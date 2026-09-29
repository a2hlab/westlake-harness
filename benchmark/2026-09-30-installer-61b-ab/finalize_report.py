#!/usr/bin/env python3
"""Attach explicit human observations and verbatim machine facts to the handoff."""
from pathlib import Path
import json,shutil
R=Path(__file__).resolve().parent
d=json.loads((R/'results.json').read_text());v=json.loads((R/'visual-review.json').read_text())
assert len(v)==17 and d['only_installer_changed']
selection=json.loads((R/'combined/selection.json').read_text());shutil.copy2(R/'combined/selection.json',R/'evidence/selection.json')
for a in d['apps']:a['visual_observation']=v[a['key']]['t20']
d['r2']={'deployment_and_fingerprint':'verified','permission_grants':'verified','all_original_14_activation_walls':'partially: 12 linked allow; Thunderbird/K9 transition unobserved','screenshots':'captured; outer visual review pending'}
d['selection']=selection
d['limitations']=['Reboot and reinstall/app-state/order covariates; this is not a randomized trial.','No linked activation observed for fd-android, fd-k9, fd-fitness and helloworld.','Alive/foreground_unconfirmed does not establish UI lighting.']
(R/'results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for n,run in enumerate(('installer-r17p-61b','installer-r17p-61b-resume'),1):
 src=R/'runs'/run/'61b0657200000000000000000324012c';out=R/'evidence'/f'source-run-{n}';out.mkdir(exist_ok=True)
 for name in ('preflight.json','runtime-fingerprint.txt','facts.txt','summary.json','plan.json'):
  shutil.copy2(src/name,out/name)
for kind in ('verify-final','pin-jar'):
 src=sorted((R/'board').glob(kind+'-*/receipt.json'),key=lambda p:p.stat().st_mtime)[-1]
 shutil.copy2(src,R/'evidence'/f'{kind}-receipt.json')
marker='## Final observations\n'
p=R/'README.md';text=p.read_text().split(marker)[0]
text+=marker+'\n17/17 grants; 13/17 linked WMS allows; zero linked background denials. Of the originally blocked 14 keys, 12 have a linked allow; Thunderbird and K9 have no observed subsequent activation in this capture. All 16 available A/B APKs and launcher entries match (HelloWorld has no A-sweep counterpart). Only the installer pair differs across the 117 fingerprint paths. R2: deployment/grants verified; universal activation recovery partially verified; visual sign-off pending outer review.\n\n'
text+='Tusky has a full login page. Thunderbird/K9 show the database-upgrade page; completion is unproven. File Manager has navigation chrome and empty content. AppManager is white, unlike A\'s verifying page. Wikipedia/Noice/Markor/Gallery/SPD/BinaryEye/VLC show the OH desktop at t20. No native repair is inferred from this installer-only run.\n\n'
text+='```text\n'+d['facts_verbatim']+'```\n\n'
text+='| Key | BMS grant | Linked WMS allow | t20 observation / archived screenshot |\n|---|---|---|---|\n'
for a in d['apps']:
 key=a['key'];text+=f"| {key} | {a['background_permission']} | {'yes' if a['linked_allow'] else 'unobserved'} | [{a['visual_observation']}](evidence/{key}/t20.jpeg) |\n"
text+='\nOriginal absolute t20 paths and exact per-app facts lines are in [PER-APP.md](PER-APP.md); full matching trace excerpts are in each evidence directory. 61b was unlocked immediately after final readback, retaining the accepted installer + original v3c + r17p. No push.\n'
p.write_text(text)
lines=['# Original t20 paths and verbatim facts','']
facts={l.split()[0]:l for l in d['facts_verbatim'].splitlines() if ' shots ' in l}
for a in d['apps']:
 key=a['key'];lines += [f'## {key}','',f"t20: `{a['t20_path']}`",'', '```text',facts[key],'```','']
(R/'PER-APP.md').write_text('\n'.join(lines))
print('Final report:',R/'README.md')
