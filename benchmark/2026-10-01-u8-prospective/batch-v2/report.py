"""Deterministic donor-qualified batch list; no deployment or freeze output."""

import argparse
import base64
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

DECISIONS = {
    'flutter-field-id': ('N10', 'prior-bundle-movement', ['fd-fluffychat','fd-immich','fd-libre','fd-saber'], [],
        'Reuse N8 existing-owner EGL/native routing as a bundle. Four engine-launch walls moved in the N8/J6 window, not an isolated EGL-field repair. Immich then hit ATrace_beginSection; Libre hit MediaStore already addressed by retained T7d. No new U8 light is proved.'),
    'flutter-private-runtime': ('N10', 'prior-bundle-movement', ['fd-kitchenowl','localsend'], [],
        'Reuse the N8 Flutter private-domain runtime/owner closure. N8/J6 advanced both to white windows. Recheck the new N10 owner identity and N2 domain closure; first-wall movement is not t20 success.'),
    'private-zlib': ('N10', 'implementation-present-visibility-conditional', [], ['burgerking','fd-im-vector-app'],
        'Reuse the private libz facade and resident libshared_libz owner route, never the root alias that regressed ZigZag. Element relocation is a direct target; BurgerKing System.exit follows caught MMKV ULE but causal sufficiency is unproved. Check each consumer domain separately; N8 did not complete Element or McDonalds.'),
    'browser-disappeared': ('N10', 'earlier-clue-not-terminal-root', [], [],
        'N8 __gnu_strerror_r is a reusable ABI candidate, but both first terminal roots remain unknown. Firefox still disappeared in N8/J6 and Fennec did not complete. Do not predict a known first-wall removal from an earlier symbol warning.'),
    'white-A': ('N10', 'bridge-owner-repair-pending', [], ['wikipedia'],
        'Include the two-bridge repair dependency, not a completed patch. wikipedia is the direct non-last-session target. fd-AppManager has one U7 session and no BBQ null, so its movement stays unknown. Existing loader/ELF idioms are not verified same-wall fixes. Latest 08:28 correction supersedes the old fresh-dlopen attribution.'),
    'white-B1': ('N10', 'bridge-owner-repair-pending', [], ['fd-app','fd-shatteredpixeldungeon'],
        'Both GLSurfaceView valid-Surface IAEs are direct bridge-owner targets. Only after the same JNI-created owner serves re-query may their current window wall move; no final t20 claim before a built candidate and signed captures.'),
    'white-B2': ('deferred', 'none', [], [],
        'Termux finishes its first Activity before window add. It has no matching valid-Surface IAE. Do not merge it into B1 or credit a bridge fix; no verified lifecycle donor located.'),
    'bitmap-color-space': ('N10', 'none-for-current-wall', [], [],
        'Hold native singleton slot. The offset-based registration probe is not a portable repair and the fallback returns null. No verified Bitmap color-space implementation located; do not ship the null fallback as a fix.'),
    'jitsi-abort-symbol': ('N10', 'implementation-present-visibility-conditional', [], ['fd-meet'],
        'Reuse android_set_abort_message from the real-work Bionic adapter, not a new stub. Move fd-meet only if its libc++_shared consumer can resolve that export in its own domain. Existing implementation alone did not prevent U7 failure.'),
    'opensles-engine': ('N10', 'provider-route-unverified', [], ['mindustry'],
        'Existing IID shim plus platform OH engine forwarding is a route candidate, not an engine implementation. N4 already attempted provider publication and U7 still misses slCreateEngine. Reuse the real OH owner only after consumer relocation/singleton proof; do not create a renamed second engine just to satisfy NEEDED.'),
    'unity-mediandk': ('N10', 'presence-only-conditional', [], ['subwaysurfers'],
        'Use real-work mediandk-presence only if exact consumer undefined imports prove no AMedia/AImage API is required. Adjacent missing libmediandk is a clue to the Unity FatalError, not a complete dependency audit. Reject historical null/error media API stub; otherwise no real API donor located.'),
    'system-exit-unknown': ('J8', 'earlier-clue-not-terminal-root', [], [],
        'Requested J8 slot for ppsspp/vlc; first System.exit roots remain unknown. PPSSPP android_dlopen_ext candidate belongs to N10, not a Java fix. VLC later AppCompat exception/theme probe cannot replace its earlier exit. Cross-layer clues do not establish first-wall movement.'),
    'appcompat-theme': ('J8', 'probe-reference-not-verified-repair', [], ['fd-api'],
        'Reuse numeric ActivityInfo theme propagation and investigate the existing probe shared app/framework asset context before lifecycle. Probe fixed IDs and synthetic attributes are not production donors. Movement is conditional on actual APK theme/attribute resolution, not merely calling setTheme.'),
    'mcd-datasource-null': ('J8', 'none-for-current-wall', [], [],
        'No donor for the DataSourceModule provider null. zlib/owner candidates are N10 secondary dependencies, not a JAR repair for this NPE. Leave the requested J8 slot unfilled rather than write a guessed provider.'),
    'nextcloud-accountmanager-null': ('J8', 'partial-service-donor', [], ['fd-client'],
        'Reuse LocalServiceBinders account service boundary (empty accounts is truthful), but prove Context.getSystemService returns a nonnull AccountManager client to SessionMixin. Binder existence alone is not a client factory repair; current same-wall fix is unverified.'),
    'osmand-map-info-null': ('J8', 'verified-secondary-function-only', [], [],
        'ColorMatrix copy implementation passed the accepted host copy/no-alias probe; reuse only if missing in the final J8 source. It addresses an earlier caught exception, not terminal MapInfoLayer null. No verified terminal-wall donor located; do not forecast fd-plus first-wall movement.'),
    'webview-provider': ('J8', 'partial-service-donor', [], ['fd-tutanota'],
        'Existing WebViewUpdateServiceAdapter supplies provider PackageInfo when installed. Verify WebViewFactory preconditions, provider APK/native closure and classloader first. This is a partial service donor, not a proved repair of the factory UnsupportedOperationException.'),
    'installer-no-bm-record': ('J8', 'input-preflight-only', [], [],
        'Payload marker plus restoration of three Seal ZIP sidecars can fix input inventory/ELF admission. It does not repair the U7 bm dump missing-record app_failed wall. Require restore receipt and actual-root resolve before freeze; installer first-wall movement unknown.'),
    'toutiao-boolean-null': ('J8', 'input-preflight-only', [], [],
        'Restore libcvt.so as explicit payload, not AArch64 executable code. This repairs input admission only, not MainActivity Boolean null. Keep the terminal wall forecast unchanged unless another verified donor is supplied.'),
    'black-content': ('deferred', 'none', [], [], 'fd-mobile black content has no matching B1 IAE or verified repair donor; do not infer bridge repair from generic unknown-session noise.'),
    'breezy-getclass-null': ('deferred', 'none', [], [], 'No verified donor for pa0.G getClass null in the bounded trees; keep current wall.'),
    'wifi-country-null': ('deferred', 'none', [], [], 'No verified donor for CountryPreference getClass null in the bounded trees; keep current wall.'),
    'x-di-null': ('deferred', 'none', [], [], 'No verified donor for the Dagger/m.a dependency null in the bounded trees; keep current wall.'),
}

EXTRA_SOURCES = {
    'white-A': ['bridge-loaded-object-idiom','bridge-namespace-idiom'],
    'white-B1': ['bridge-loaded-object-idiom','bridge-namespace-idiom'],
    'appcompat-theme': ['theme-probe-reference'],
    'system-exit-unknown': ['theme-probe-reference'],
    'unity-mediandk': ['mediandk-error-stub'],
    'opensles-engine': ['n8-owner-route'],
}


def load_intake():
    return json.loads(gzip.decompress(base64.b64decode((HERE/'intake.json.gz.b64').read_bytes())))


def build(intake):
    rows = []
    for cluster in intake['clusters']:
        groups = [('white-B1', [app for app in cluster['apps'] if app['key'] != 'termux']),
                  ('white-B2', [app for app in cluster['apps'] if app['key'] == 'termux'])] if cluster['id']=='white-B' else [(cluster['id'],cluster['apps'])]
        for identifier, apps in groups:
            batch, grade, likely, conditional, rationale = DECISIONS[identifier]
            sources = list(dict.fromkeys(cluster['source_ids'] + EXTRA_SOURCES.get(identifier, [])))
            rows.append(dict(id=identifier,parent_cluster=cluster['id'],wall=cluster['wall'],layer=cluster['layer'],
                             batch=batch,count=len(apps),apps=apps,donor_ids=sources,donor_grade=grade,
                             predicted_first_wall_moves=likely,conditional_first_wall_moves=conditional,
                             unknown_or_not_targeted=[app['key'] for app in apps if app['key'] not in likely+conditional],
                             rationale=rationale,built_verified_fix=False))
    rows.sort(key=lambda row:(-row['count'],row['id']))
    return dict(schema_version=2,status='batch-list-before-prediction-freeze',freeze_authorized=False,expected_run_created=False,
                supersedes=dict(directory='draft-v1',csv_sha256='9540f9332f29281362a6be6ffacb3338a4132dccfceaa4d76d73b0bf3c1d3a36',
                                authority='outer ACK95 2026-10-01 08:21:00',meaning='historical narrow draft; MUST NOT execute or score as U8'),
                source_cluster_count=len(intake['clusters']),batch_row_count=len(rows),key_count=sum(row['count'] for row in rows),
                route_counts=dict(Counter({batch:sum(row['count'] for row in rows if row['batch']==batch) for batch in ['N10','J8','deferred']})),
                clusters_sha256=intake['clusters_sha256'],intake_sha256=hashlib.sha256((HERE/'intake.json.gz.b64').read_bytes()).hexdigest(),
                batches=rows,donors=intake['sources'],n8=intake['n8'],payload=intake['payload'],bridge_candidate=intake['bridge_candidate'],
                limitations=[intake['remote_search'],'Batch assignment is a proposed integration slot, not permission to ship an unverified donor.',
                             'Only six N8 Flutter keys have prior bundle-level wall movement, under J6 rather than U7/U8.',
                             'No N10/J8 runtime artifacts exist in this delivery. Gate grants and expected-run must bind final built bytes.',
                             '08:28:40 outer correction: resident runtime resolver is NOLOAD-only; actual second-owner loading point unknown. Candidate C paused pending owner selection.',
                             'Thirty-four signed-bright U7 keys are regression controls; final sixty-six-key first-wall/checkpoint/t20 predictions come later.'])


def markdown(result):
    lines = ['# U8 batch-v2: N10 native + J8 Java/input intake', '',
             '**Unfrozen batch list.** The 08:21 dispatch supersedes the narrow N8 + payload draft. A source candidate was previously easy to mistake for a proven first-wall repair; this list separates them. No expected-run, new CSV, runtime build or input move is made here.', '',
             '## Population and publication units', '',
             f"- {result['source_cluster_count']} accepted clusters / {result['key_count']} U7 unlit keys; white-B split makes {result['batch_row_count']} rows.",
             '- Requested slots: N10 18 keys, J8 9, deferred 5. Counts are targets, **not unlocked apps**.',
             '- N10: one native batch, N8 native-only delta plus qualified singleton and bridge-owner repairs. Never import the embedded old N8 runtime JAR or root libz alias.',
             '- J8: one Java batch retaining U7/T7d coverage, plus separately hashed payload-marker tooling and two restored-input identities. Payload tooling/input files are **not JAR contents**.',
             '- Six Flutter keys have prior N8/J6 wall movement. All other movements below are conditional or unknown; no N10/J8 lighting result is claimed.', '',
             '## Cluster batch table', '',
             '| Cluster / layer | Keys | Batch | Donor IDs (full paths/commits below) | First-wall forecast | Qualification |',
             '|---|---|---|---|---|---|']
    for row in result['batches']:
        movement = 'likely: '+(', '.join(row['predicted_first_wall_moves']) or 'none')+'; conditional: '+(', '.join(row['conditional_first_wall_moves']) or 'none')+'; unknown/not targeted: '+(', '.join(row['unknown_or_not_targeted']) or 'none')
        lines.append('| '+ ' | '.join([row['id']+' / '+row['layer'], ', '.join(app['key'] for app in row['apps']),row['batch'],', '.join(row['donor_ids']) or 'none',movement,row['donor_grade']])+ ' |')
    lines.extend(['','## Row evidence and conditions',''])
    for row in result['batches']:
        lines.extend(['### '+row['id'],'',row['rationale'],''])
        for app in row['apps']:
            evidence = '; '.join('`'+entry['file']+':'+str(entry['line'])+'`' for entry in app['evidence'])
            lines.append('- **'+app['key']+'**: signed '+app['visual']+'; '+app['terminal_status']+' / '+app['root_status']+'. '+evidence)
        lines.append('')
    lines.extend(['## Donor path/commit ledger','','Paths are relative to the named tree under `WORKSPACES`; full file SHA and bounded excerpts are in `results.json`. A last-change commit is not a claim of board validation.','','| ID | Tree / path:line | Snapshot / last change | Scope |','|---|---|---|---|'])
    for identifier, donor in sorted(result['donors'].items()):
        line = donor['excerpt'][0]['line'] if donor['excerpt'] else 1
        lines.append('| '+identifier+' | '+donor['repository']+' / `'+donor['path']+':'+str(line)+'` | `'+donor['commit']+'` / `'+donor['last_change_commit']+'` | '+donor['note'].replace('|','/')+' |')
    lines.extend(['','## Bridge correction and owner handoff','',
                  '- cc-t3 donor/diff: `benchmark/2026-09-30-u4-sweep/COMPOSE-WALL.md:1042`, commit `'+result['bridge_candidate']['commit']+'`. The wl_critfix idiom has reported prior DAYU600 use; its bridge application is not built or tested.',
                  '- Outer 08:28:40 accepts cx-t0: runtime `216b68fb` uses N2 source `b94f69e4` (`42b5f71b8`), resolver has only NOW/NOLOAD. Old snapshot fresh-dlopen line 433 is **not** current runtime causality. Both runtime and bridge have two copies; actual loader origin remains unknown.',
                  '- Therefore selecting the first basename match or keeping a pointer in one runtime static global does not prove the correct JNI owner. Candidate C is paused. cx-t0/cc-wiki own loader-domain resolution; do not copy the historical implementation blindly.',
                  '- Keep bridge `84695d62` unchanged until #96 reproducible build-chain acceptance. Direct conditional targets: wikipedia, fd-app, fd-shatteredpixeldungeon. AppManager remains unknown; Termux is B2, outside this mechanism.', '',
                  '## Payload and freeze prerequisites','',
                  '- Native candidate manifest: `'+result['n8']['manifest_sha256']+'`; final N10 must have a new manifest and independent N1/N2 approval.',
                  '- Payload source: `'+result['payload']['commit']+'`, `'+result['payload']['path']+'`; corrected tests `'+result['payload']['tests_commit']+'`. Marker skips ELF admission only, not hashes, sizes, paths or inventory.',
                  '- Intake observed active Seal 6 / Toutiao 137; quarantined additions 3 / 1, target 9 / 138. This lane moved nothing and has no post-restore resolve receipt. ZIP payload is not native code; ELF32 payload is not ARM64 support.',
                  '- Freeze only after final N10/J8 hashes, same-owner evidence, qualified donor regression, restored actual-root inventories and full runner resolve. Then create the **new** 66-key CSV/SHA and expected-run; three scoring axes stay separate.',
                  '- Historical draft-v1 SHA `'+result['supersedes']['csv_sha256']+'` is superseded, never an active freeze. Old local skeleton/draft files are excluded from this landing manifest.', '',
                  '## Verification and scope','',
                  '`python3 batch-v2/test_batches.py -v` replays pinned evidence without donor trees or devices. `search_donors.py` and `collect.py --searches <receipt.json>` are optional read-only recollection tools; no remote search was run.',
                  'See `validation.json` for actual gate receipts; software checks cannot promote candidates to device-verified repairs.',''])
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--format', choices=['json','markdown'], default='json')
    args = parser.parse_args()
    result = build(load_intake())
    print(markdown(result), end='') if args.format=='markdown' else print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
