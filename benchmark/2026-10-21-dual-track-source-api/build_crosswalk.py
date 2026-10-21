#!/usr/bin/env python3
"""G11 dual-track source/build/API crosswalk (draft; the authoritative table is NOT modified).

Reads the main repository READ-ONLY (--source-root, default: sibling westlake-harness checkout) and
records the exact SHA256/bytes of every referenced file. A missing reference or an unexpected hash
becomes an explicit gap; nothing is upgraded. Writes only beside this script:
crosswalk.json (draft rows in the api-progress-observations/v1 row shape + crosswalk fields),
crosswalk.md, gaps.json. No device, no REA, no build, no T38 code or test is executed.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OBS = 'benchmark/2026-10-19-api-progress-update'
ATLAS = 'benchmark/2026-10-14-api-source-delivery'
AE = 'benchmark/2026-10-21-commercial-game/apk-extractor'
MV = 'benchmark/2026-10-21-manual-video-regression'

def refs(base, names): return [f'{base}/{n}' for n in names]

ROWS = [
 dict(id='DRAFT-G08-ZIP-COMMENT', track='commercial-game (Genshin)', api_class='public OH system component (installd libinstalls ZIP parsing); not an Android API',
      related_atlas='JAVA-042 (same 安装/校验 family; atlas gap already notes libinstalls is not libapk_installer)', commits=['66b4e0a27a', '44b05158d1'],
      name='G08 locate/validate APK ZIP comment in installd zip_file.cpp',
      status='OFFLINE_SOURCE_REPRO_AND_BOUNDARY_TESTS_PASS; host Open only; as of receipt apk-extractor/results.json: device_install NOT_TESTED_WITH_PATCH, game_runtime NOT_STARTED',
      apps='Genshin APK abd3c4d5 (513290344 B): host-side parse/Open only. Unpatched board install failed (first fatal recorded); game never started.',
      deployment='None. No patched library on any board.',
      source=refs(AE, ['comment-compatibility.patch', 'patch-origin.json', 'harness.cpp', 'zip_audit.py', 'source-index.json']),
      build=refs(AE, ['build_replay.py', 'check_boundaries.py', 'check_receipt.py']),
      evidence=refs(AE, ['README.md', 'results.json', 'SHA256SUMS', 'evidence/install-first-fatal.json'])),
 dict(id='DRAFT-G09-LIBINSTALLS-BUILD', track='commercial-game (Genshin)', api_class='public OH system component build recipe; not an Android API',
      related_atlas='JAVA-042 (recipe/archive binding gap)', commits=['7dc33a8361', '44b05158d1'],
      name='G09 reproducible libinstalls ZIP-comment build (13 steps)',
      status='BASELINE_IDENTICAL_CANDIDATE_BUILT; 13/13 steps rc0; baseline library 51e1b525 reproduced; candidate library 7c24bd11; not deployed as of receipt native-build/results.json (its deployment_authorized=false is the unsigned offline receipt field, not an absence of user deployment authorization); frozen 8 entries / 30 checks / 0 violations',
      apps='None (build only).', deployment='Not deployed as of receipt; user deployment authorization exists outside this receipt.',
      source=refs(AE, ['native-build/inputs.lock.json', 'native-build/check_inputs.py']),
      build=refs(AE, ['native-build/build_native.py', 'native-build/COMMANDS.md', 'native-build/test_recipe.py', 'native-build/manifest.json']),
      evidence=refs(AE, ['native-build/README.md', 'native-build/results.json', 'native-build/SHA256SUMS', 'outer-build-01/README.md', 'outer-build-01/results.json'])),
 dict(id='DRAFT-G09-REMOTE-ARCHIVE', track='commercial-game (Genshin)', api_class='build provenance (archive); not an API',
      related_atlas='JAVA-042 (archive binding)', commits=['f45e7ec8a7'],
      name='G09 original native build artifacts and logs archived remotely',
      status='REMOTE_VERIFIED c7ad6186 (10867480 B, 551 payload members, no APK)',
      apps='None.', deployment='Archive only.',
      source=[], build=refs(AE, ['native-build/remote-confirmation/argv.json', 'native-build/remote-confirmation/records.json']),
      evidence=refs(AE, ['native-build/archive-receipt.json', 'native-build/remote-confirmation/receipt.json', 'native-build/remote-confirmation/verified.json', 'native-build/remote-confirmation/raw-index.json'])),
 dict(id='DRAFT-T35-WHITESCREEN', track='Toutiao video (61b)', api_class='app-specific guardian evidence (host script); not an Android API',
      related_atlas='none', commits=['5824a0a99c', '06c26e2fcb'],
      name='T35 61b white host after user close + icon; video-freeze report withdrawn',
      status='WHITE_SCREEN_OBSERVED; cause INFERRED_STATIC (stale WL_PARENT_ID gate); live parent environ NOT_OBSERVED (tool failure + safety stop, not retried)',
      apps='Toutiao 61b: white host observed; prior video playback report withdrawn by user.', deployment='r3 guardian 8bf74a08 deployed; unchanged.',
      source=[], build=[], evidence=refs(MV, ['README.md', 'results.json', 'whitescreen-01/README.md', 'whitescreen-01/results.json'])),
 dict(id='DRAFT-T36-R4C-CANDIDATE', track='Toutiao video (61b)', api_class='app-specific guardian candidate; not an Android API',
      related_atlas='none', commits=['db5ebfa0c1'],
      name='T36 r4c host-recreation parent-epoch switch candidate (r4/r4b failed versions retained)',
      status='OFFLINE_CANDIDATE; NOT_DEPLOYED as of receipt host-reentry-candidate/results.json; white screen NOT fixed on device',
      apps='None on device.', deployment='Not deployed.',
      source=refs(f'{MV}/host-reentry-candidate', ['src/watchdog-reentry-r4c.sh', 'src/reentry-common-r4.sh', 'src/watchdog-reentry-r4b.sh', 'src/watchdog-reentry-r4.sh']),
      build=refs(f'{MV}/host-reentry-candidate', ['tests/assemble-payload.py', 'candidate-package-r4c/MANIFEST.sha256']),
      evidence=refs(f'{MV}/host-reentry-candidate', ['README.md', 'results.json'])),
 dict(id='DRAFT-T37-PEER-REVIEW', track='Toutiao video (61b)', api_class='app-specific guardian review; not an Android API',
      related_atlas='none', commits=['53e5c670aa', '0d251eae18'],
      name='T37 independent counterexamples, r4c 18/18 function replay, 165 assembly checks, migration review',
      status='OFFLINE_REVIEW_PASS for r4c functions/assembly; device acceptance PENDING',
      apps='None on device.', deployment='None.',
      source=[], build=refs(f'{MV}/host-reentry-peer', ['candidate_review.py', 'assembly_audit.py']),
      evidence=refs(f'{MV}/host-reentry-peer', ['README.md', 'results.json', 'acceptance-matrix.json', 't38-appendix/INITIAL-REVIEW.md'])),
    dict(id='DRAFT-T38-WINDOW', track='Toutiao video (61b)', api_class='app-specific guardian device window (plan/archive); not an Android API',
      related_atlas='none', commits=['d2ff2fa9e9'],
      name='T38 r4c new-ROOT disabled plan, 61b read-only fresh, two safety stops',
      status='UNVALIDATED; deploy.py v2 UNVALIDATED; no orchestration code; window not executed as of receipt host-reentry-window/results.json; no device fix acceptance',
      apps='None on device (read-only fresh only).', deployment='None; r3 guardian unchanged on 61b.',
      source=[], build=refs(f'{MV}/host-reentry-window', ['deployment/deploy.py', 'deployment/prepare.py', 'deployment/mechanical.diff']),
      evidence=refs(f'{MV}/host-reentry-window', ['README.md', 'results.json', 'SAFETY-STOP-20261021T1731.md', 't36-landing.json'])),
 dict(id='DRAFT-G12-WINDOW-PREP', track='commercial-game (Genshin)', api_class='public OH system component deployment preparation; not an Android API',
      related_atlas='JAVA-042', commits=['9084435f65'],
      name='G12 installer window preparation and fresh review evidence',
      status='OFFLINE_PREPARATION; fresh read-only evidence; no install',
      apps='None.', deployment='None.',
      source=refs(f'{AE}/window-prep', ['sources.json']), build=refs(f'{AE}/window-prep', ['build-proof.json']),
      evidence=refs(f'{AE}/window-prep', ['README.md', 'fresh-review.json', 'fresh-next-review.json'])),
 dict(id='DRAFT-G13-DEVICE-WINDOW', track='commercial-game (Genshin)', api_class='public OH system component guarded install transaction; not an Android API',
      related_atlas='JAVA-042', commits=['9084435f65'],
      name='G13 guarded single-library installer window (offline delivery)',
      status='OFFLINE_DELIVERY; device phases not executed as of receipt device-window/results.json (DISABLED_EXECUTOR_READY_FOR_OUTER_REVIEW); later: outer reported a 5ea G13 window opened 17:47:10 (+0800), before rc0, control running, no apply/install yet - not yet in main receipts',
      apps='As of receipt: Genshin not installed with patch, not started.', deployment='None as of receipt; live 5ea window in progress per outer report (not reflected here).',
      source=refs(f'{AE}/device-window', ['transaction.py']), build=refs(f'{AE}/device-window', ['prepare.py', 'run_window.py', 'OPERATIONS.zh-CN.md']),
      evidence=refs(f'{AE}/device-window', ['README.md', 'results.json'])),
]
INPUTS = [f'{OBS}/observations.json', f'{OBS}/render.py', f'{ATLAS}/views/api-progress.json', f'{ATLAS}/views/source-delivery.json']

def digest(root, rel):
    p = root / rel
    if not p.is_file() or p.is_symlink(): return None
    b = p.read_bytes(); return {'path': rel, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args(); root = a.source_root.resolve()
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    gaps, rows = [], []
    for spec in ROWS:
        row = {k: spec[k] for k in ('id', 'track', 'api_class', 'related_atlas', 'commits', 'name', 'status', 'apps', 'deployment')}
        row['kind'] = 'draft crosswalk observation; not merged into the authoritative table'
        row['frozen'] = False
        for g in ('source', 'build', 'evidence'):
            row[g] = []
            for rel in spec[g]:
                d = digest(root, rel)
                if d is None: gaps.append({'row': spec['id'], 'group': g, 'path': rel, 'gap': 'missing in main'})
                else: row[g].append(d)
        row['observed_status'] = {}
        for e in row['evidence']:
            if e['path'].endswith('results.json'):
                try: row['observed_status'][e['path']] = json.loads((root / e['path']).read_text()).get('status', '<no status key>')
                except Exception as x: row['observed_status'][e['path']] = '<unreadable: %s>' % type(x).__name__
        for c in spec['commits']:
            if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', c, 'HEAD']).returncode != 0:
                gaps.append({'row': spec['id'], 'commit': c, 'gap': 'commit not an ancestor of main HEAD'})
        if not row['source']: gaps.append({'row': spec['id'], 'group': 'source', 'gap': 'no implementation source file (evidence/review/archive-only row)'})
        rows.append(row)
    atlas = json.loads((root / ATLAS / 'views/api-progress.json').read_text())
    j042 = next(r for r in atlas['rows'] if r['id'] == 'JAVA-042')
    gaps.append({'row': 'DRAFT-T38-WINDOW', 'gap': 'landed only as an archive of a disabled plan; deploy.py v2 UNVALIDATED (6/22 donor cases); orchestration not written (safety stop); window not executed as of receipt'})
    gaps.append({'row': 'DRAFT-G13-DEVICE-WINDOW', 'gap': 'as of receipt device-window/results.json: device phases not executed, no patched install, no Genshin launch; outer-reported live 5ea window (17:47:10, before rc0, control running, no apply/install) not yet in main receipts'})
    obs = json.loads((root / OBS / 'observations.json').read_text())
    gaps.append({'row': '*', 'gap': 'authoritative observations table (%d rows, as_of %s) has no G08/G09/G12/G13/JAVA-042-fix/T35-T38 row; this draft is not merged' % (len(obs['rows']), obs['as_of'])})
    gaps.append({'row': 'DRAFT-G08-ZIP-COMMENT', 'gap': 'no device install with patched libinstalls; Genshin never started; no Android reference device/API level evidence'})
    gaps.append({'row': 'DRAFT-G09-LIBINSTALLS-BUILD', 'gap': 'candidate 7c24bd11 not deployed as of receipt; JAVA-042 atlas row still lists source_location unknown / current_deployed unknown'})
    gaps.append({'row': 'DRAFT-T36-R4C-CANDIDATE', 'gap': 'white screen fix not device-verified; T38 window not executed'})
    out = dict(schema='g11-dual-track-crosswalk/v1', source_root_head=head,
               expected_input_sha256={rel: digest(root, rel)['sha256'] for rel in INPUTS},
               java042_atlas_row_sha256=hashlib.sha256(json.dumps(j042, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
               java042_atlas_status={k: j042[k] for k in ('implementation_status', 'deployment_status', 'source_location', 'route_generation')},
               rows=rows, not_substituted='historical Boat audio reuse and earlier sound confirmations are not used as current evidence for any row',
               status_semantics='Every not-executed/not-deployed statement is a snapshot as of the cited receipt at the recorded main HEAD; later live execution is not negated by these rows.',
               device_calls=0, rea_calls=0, builds=0)
    (HERE / 'crosswalk.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    (HERE / 'gaps.json').write_text(json.dumps(gaps, indent=1, ensure_ascii=False) + '\n')
    md = ['| id | track | class | status | main commits | refs (src/build/evidence) |', '|---|---|---|---|---|---|']
    for r in rows:
        md.append(f"| {r['id']} | {r['track']} | {r['api_class']} | {r['status']} | {' '.join(r['commits'])} | {len(r['source'])}/{len(r['build'])}/{len(r['evidence'])} |")
    (HERE / 'crosswalk.md').write_text('\n'.join(md) + '\n')
    n = sum(len(r[g]) for r in rows for g in ('source', 'build', 'evidence'))
    print(json.dumps({'main_head': head, 'rows': len(rows), 'main_refs': n, 'gaps': len(gaps)}))

if __name__ == '__main__':
    main()
