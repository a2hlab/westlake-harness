#!/usr/bin/env python3
"""Append one T32 observation from a read-only MAIN checkout."""
import argparse, hashlib, json, shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2]; main=a.source_root.resolve()
rel=Path('benchmark/2026-10-19-api-progress-update');out=root/rel;src=main/rel
review=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def refs(prefix,names):
 return [{'path':str(Path(prefix)/n),'sha256':sha(main/prefix/n)} for n in names]
data=json.loads((src/'observations.json').read_text());assert len(data['rows'])==43
row={
'id':'OBS-20261020-T32-HOST-PAGE',
'kind':'host-page deployment observation; not a new public API',
'name':'T32: one normal icon opens Toutiao without development host controls',
'status':'ACCEPTED_RETAINED_5CD_HOST_PAGE; SINGLE_ICON_TO_TRUE_FEED; COLD_START_WAIT_REMAINS; SIX_RUNTIME_CONTENTS_PRESERVED; NO_NEW_PUBLIC_API_FREEZE',
'method':'Same-signature HAP overwrite update changes only ets/pages/Index.abc to remove the Westlake development title and input field. EntryAbility and the other eight package members remain identical; original certificate/profile are preserved. Exact Linux compiler replay reproduces both original ABC files before compiling the new page; signing and verification receipts record rc0. The normal host window and Android child startup path remain in use.',
'platform':'5cd only; boot e562ad3e-f531-4582-ac24-7c5eeba5f8bb; host5687/b13733 WID29, parent5866/b13907, child7754/b15288; UID20011300 and accessTokenId537137511 preserved. Source/build commit12df0a7e59; execution contract46b381bca2.',
'apps':'One normal desktop icon tap reaches real Toutiao feed after reboot without the development title/input. Recorded short-video frames progress within the selected clip; the final screenshot is the real recommendation feed. Audio reuses the prior user confirmation of audible manual playback, with no new clip-specific hearing claim.',
'limitations':'Cold start still waits on an empty background: early samples at1.876/7.467/13.023 seconds and first sampled feed at55.867 seconds do not establish exact first-present timing or faster startup. No random-crash fix, zero-delay launch, all-video guarantee, new playback-cycle acceptance or new public API is claimed. Preserved directory metadata and bundle identity do not prove all mutable data bytes identical. The readiness whitespace comparison failure and ineffective system Back action remain recorded; observed in-app back returned to feed. Original T31 signoff and historical315 semantics remain unchanged.',
'deployment':'Candidate HAP b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0 retained over exact rollback HAP df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a via bm install -r -p, without uninstall/data clear. Six T31 runtime contents match physically and in parent private namespace. UID/GID/appId/appIdentifier/token/permission states and five directory dev:inode:mode:owner identities preserved. Outer retain decision516.190393s; close516.600150s and lock released; power10000/10000 and debug absence restored. This row does not claim remote archive or Git publication verification.',
'source':refs('benchmark/2026-10-20-toutiao-launcher-page',['sources/candidate/Index.js','sources/baseline/EntryAbility.js','sources/baseline/Index.js']),
'build':refs('benchmark/2026-10-20-toutiao-launcher-page',['compile_abc.py','package_sign.py','inputs.lock.json','compile-linux-01.json','production-01.json','raw-index.json','README.md']),
'evidence':refs('benchmark/2026-10-20-t32-host-page-accepted',['README.md','results.json','retain-decision.json','closed.json','peer-closure.json','final-feed.jpeg','early-background.jpeg','video-a.jpeg','video-b.jpeg'])+refs('benchmark/2026-10-20-t31-replay-02-archive',['user-audio-confirmation.json'])+refs('specs/toutiao-launcher-transition',['t3-root-host-update.spec.md']),
'frozen':False}
data['rows'].append(row)
backup=review/'.private/pre-existing-api';backup.mkdir(parents=True,exist_ok=True)
for name in ['observations.json','README.md','render.py','index.html','observations.csv','results.json']:
 if (out/name).exists() and not (backup/name).exists():shutil.copy2(out/name,backup/name)
out.mkdir(exist_ok=True)
(out/'observations.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
shutil.copy2(src/'render.py',out/'render.py')
n=sum(len(r[k]) for r in data['rows'] for k in ('source','build','evidence'))
text=(src/'README.md').read_text().replace('43 observations with 1052 exact source/build/evidence references',f'44 observations with {n} exact source/build/evidence references')
text+='\nT32 adds one host-page deployment observation: one normal icon reaches Toutiao without the development title/input, while cold-start waiting remains. Exact ABC replay/signing and the retained HAP are recorded separately from live evidence. Six retained T31 runtime contents and bundle/directory identities are preserved; short-video image progression and prior user audio confirmation are scoped as recorded. This does not claim a random-crash fix, faster startup, all-video success or a new public API. The first43 observation objects remain unchanged.\n'
(out/'README.md').write_text(text)
(review/'baseline.json').write_text(json.dumps({'main_observations_sha256':sha(src/'observations.json'),'renderer_sha256':sha(src/'render.py'),'old_rows':43,'new_references':sum(len(row[k]) for k in ('source','build','evidence'))},indent=2)+'\n')
print('Prepared44 rows;',n,'references')
