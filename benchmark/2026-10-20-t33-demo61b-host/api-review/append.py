#!/usr/bin/env python3
"""Append T33 to the exact44-row MAIN observation baseline; no device access."""
import argparse,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);a=p.parse_args()
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];main=a.source_root.resolve()
rel=Path('benchmark/2026-10-19-api-progress-update');out=ROOT/rel
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def refs(prefix,names):return [{'path':str(Path(prefix)/n),'sha256':sha(main/prefix/n)} for n in names]
b=json.loads((main/rel/'observations.json').read_text());assert len(b['rows'])==44
source_row=b['rows'][-1];assert source_row['id']=='OBS-20261020-T32-HOST-PAGE'
a_rel='benchmark/2026-10-20-t33-demo61b-host/accepted'
e=json.loads((main/a_rel/'results.json').read_text());assert e['status']=='ACCEPTED_RETAINED_61B_HOST_PAGE_ONLY'
assert e['video_runtime_transferred'] is False and e['new_video_acceptance'] is False
archive=json.loads((main/a_rel/'archive.json').read_text());assert archive['status']=='REMOTE_ARCHIVE_AND_ALL_MEMBERS_VERIFIED'
row={
'id':'OBS-20261020-T33-DEMO61B-HOST-PAGE',
'kind':'61b host-page deployment observation; not a new public API',
'name':'T33: the 61b demo icon reaches Toutiao without development host controls',
'status':'ACCEPTED_RETAINED_61B_HOST_PAGE_ONLY; ONE_NORMAL_ICON_TO_TRUE_FEED; VIDEO_RUNTIME_TRANSFER_FALSE; NEW_VIDEO_ACCEPTANCE_FALSE; COLD_START_WAIT_REMAINS; NO_NEW_PUBLIC_API_FREEZE',
'method':'Reuse the exact T32 signed HAP b18978b8 after the61b installed HAP matched complete df385638 original bytes. Only ets/pages/Index.abc changes among9 package members; original certificate/profile and EntryAbility are preserved. T32 source/compiler replay/signing receipts are reused, not a new build. The61b-specific executor preserves this board\'s own runtime, UID/token, guardian and data identities; unchanged real-start-parent-bounded.sh performs the existing single WL_PARENT_ID33-to30 derivation.',
'platform':'61b only; boot3394710e-965c-47cc-a9f5-2b06f3d6c3f1, host4859/b6415/WID30, parent5066/b6658, child7039/b8160; parent namespace4026532996. UID20011206 and accessTokenId537243994 unchanged. Static executor commit684032d449; contract33687ff32. No5cd/5ea operation in this observation.',
'apps':'One normal desktop Toutiao icon tap after reboot: three early empty-background samples without the development title/input, followed by two real recommendation-feed images. Final feed348e80b9 was personally viewed for this API review. This host-page-only window supplies no new video or audio acceptance;5cd playback evidence is not transferred to61b.',
'limitations':'Cold start still waits. First sampled feed at74.338759 seconds is not exact first-frame timing or a performance improvement. No random-crash fix, all-video guarantee, new61b playback success or public-API freeze is claimed. The same app on two boards is not two distinct apps. Directory metadata/labels and bundle identity preservation do not establish every mutable data byte unchanged. facts.txt aggregate runtime/bootimage/tool and liveness fields remain unknown; exact before/final runtime checks are separate evidence. Rollback prechecks reject foreign identity/data/runtime drift; no unconditional recovery claim.',
'deployment':'Same-signature bm install -r -p retains HAPb18978b8 over exact rollbackdf385638, without uninstall/data clear. Four recorded libraries and initcfg remain byte-identical, OpenSLES compat remains absent,18 guardian files and installed package list unchanged. run.sh d3518cef becomes6afd6fba solely through the existing WID33-to30 field change; physical/private hashes and inodes are checked. Five directory identities/labels, UID/GID/token/permissions remain. Outer retained at325.996781s and closed at326.466225s; lock released, original power30000/86400000 and debug absence restored. Public archive receipt reports remote SHA'+archive['sha256']+' verified,1078510 bytes/7465 members; this review performs no new remote access. No remote Git push claimed.',
'source':source_row['source']+refs('benchmark/2026-10-20-t33-demo61b-host/static',['window_ops.py']),
'build':source_row['build'],
'evidence':refs(a_rel,['README.md','results.json','retain-decision.json','closed.json','peer-closure.json','unlock-verified.json','facts.txt','early-background.jpeg','first-feed.jpeg','final-feed.jpeg','archive.json','archive-members.json'])+refs('specs/toutiao-launcher-transition',['t4-demo61b-host-update.spec.md']),
'frozen':False}
backup=HERE/'.private/baseline';backup.mkdir(parents=True,exist_ok=True)
for name in ['observations.json','README.md','render.py']:
 q=backup/name
 assert not q.exists() or q.read_bytes()==(main/rel/name).read_bytes(),'baseline already frozen differently'
 if not q.exists():shutil.copy2(main/rel/name,q)
b['rows'].append(row);out.mkdir(exist_ok=True)
(out/'observations.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
shutil.copy2(main/rel/'render.py',out/'render.py')
count=sum(len(r[k]) for r in b['rows'] for k in ['source','build','evidence'])
text=(main/rel/'README.md').read_text().replace('44 observations with 1073 exact',f'45 observations with {count} exact')
text+='\nT33 propagates only the accepted host HAP to61b. One normal icon reaches real feed without development controls; cold-start waiting remains. The61b runtime/guardian/data identities are preserved, with the original single WID field derivation33-to30. No5cd video runtime transfer or new61b video/audio acceptance is claimed. The first sampled feed at74.339 seconds is not exact startup latency. All44 preceding observation objects and historical315 semantics remain unchanged.\n'
(out/'README.md').write_text(text)
(HERE/'baseline.json').write_text(json.dumps({'observations_sha256':sha(main/rel/'observations.json'),'renderer_sha256':sha(main/rel/'render.py'),'old_rows':44,'new_references':sum(len(row[k]) for k in ['source','build','evidence'])},indent=2)+'\n')
print('Prepared45 rows;',count,'references')
