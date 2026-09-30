#!/usr/bin/env python3
"""Descriptive cross-profile feedback; never edits a freeze or image verdict."""
import collections
import csv
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from extract_unified_failures import SOURCE, RUN, OUT, sha
from scan_installer_background import scan as background_scan
from rules_unified_r17r import FAMILY

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'2026-09-30-r17op-execution-revision'))
import profile_audit
from audit_run import record_facts
FREEZE = profile_audit.FREEZE


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def actual_family(row):
    if row['lit']:
        return 'none-signed-lit'
    if row['stage'] == 'prelaunch':
        return 'input-identity' if 'identity' in (row['record_error'] or '') else 'input-non-aarch64-elf'
    text = '\n'.join(x['text'] for x in row['chain'])
    checks = [
        ('SoundPool.<clinit>', FAMILY), ('AudioProductStrategy.native_list_', FAMILY),
        ('EGL_NO_SURFACE', 'egl-window-recreation'),
        ('libjnidispatch.so', 'jna-native-resource'),
        ('Error loading shared library', 'app-native-namespace-dependency'),
        ('Error relocating', 'bionic-symbol'),
        ('Sentry', 'sentry-provider-configuration'),
        ('VerifyError', 'dex-verifier-access'),
        ('maxSizeBytes', 'disk-cache-size-contract'),
        ('Failed to resolve SessionToken', 'media-session-service-resolution'),
        ('CameraX is not configured', 'camerax-configuration'),
        ('Theme.AppCompat', 'activity-theme-contract'),
        ('Failed to resolve attribute', 'activity-theme-contract'),
        ('EXTERNAL_CONTENT_URI', 'mediastore-field'),
        ('getApplicationRestrictions', 'restrictions-service-null'),
        ('SystemVibrator.getInfo', 'haptics-capability-null-array'),
        ('GLImpl._nativeClassInit', 'gles-jni'),
        ('WebViewFactory.getProvider', 'webview-provider'),
        ('AssetManager.nativeOpenAssetFd', 'asset-font-fd-stub'),
        ('Lorg/ccil/cowan/tagsoup/Parser;', 'tagsoup-api'),
        ('without a color space', 'bitmap-colorspace'),
        ('getLinkUpstreamBandwidthKbps', 'network-capabilities-method'),
    ]
    return next((family for needle, family in checks if needle in text), 'unknown-first-wall')


def prior_family(text):
    checks = [
        (r'EGL_NO_SURFACE|EGL surface', 'egl-window-recreation'),
        (r'libjnidispatch|JNA Native library', 'jna-native-resource'),
        (r'liblog|libstdc\+\+|libGLES|libOpenSLES|libandroid|Flutter dependency', 'app-native-namespace-dependency'),
        (r'__register_atfork|__errno', 'bionic-symbol'),
        (r'Theme.AppCompat', 'activity-theme-contract'),
        (r'CameraX', 'camerax-configuration'),
        (r'MediaStore', 'mediastore-field'),
        (r'RestrictionsManager', 'restrictions-service-null'),
        (r'GLImpl', 'gles-jni'), (r'WebView', 'webview-provider'),
        (r'NetworkCapabilities', 'network-capabilities-method'),
        (r'tagsoup', 'tagsoup-api'), (r'bitmap without color space', 'bitmap-colorspace'),
        (r'non-ELF|not an AArch64', 'input-non-aarch64-elf'),
    ]
    return next((family for pattern, family in checks if re.search(pattern, text, re.I)), 'other-or-unknown-prior-wall')


def lighting_metric(rows, column):
    # "advance"/unknown are not promises of darkness. Report both alert retrieval
    # and a strict subset score so abstentions cannot quietly become true negatives.
    lit = {r['key'] for r in rows if r['actual_lit']}
    predicted = {r['key'] for r in rows if r[column] == '亮'}
    strict = [r for r in rows if r[column] in ('亮', '不变')]
    return dict(samples=len(rows), actual_lit=len(lit), predicted_lit=len(predicted),
                lit_hits=len(lit & predicted), lit_false_alerts=len(predicted-lit),
                lit_not_predicted=len(lit-predicted),
                hit_keys=sorted(lit & predicted), false_alert_keys=sorted(predicted-lit),
                not_predicted_lit_keys=sorted(lit-predicted),
                lit_precision=len(lit & predicted)/len(predicted) if predicted else None,
                lit_recall=len(lit & predicted)/len(lit) if lit else None,
                strict_bright_unchanged_samples=len(strict),
                strict_correct=sum((r[column] == '亮') == r['actual_lit'] for r in strict),
                strict_abstentions=len(rows)-len(strict),
                all_not_lit_baseline=sum(not r['actual_lit'] for r in strict),
                policy='Cross-profile binary lighting only; advance/unknown are excluded from strict accuracy; unchanged is projected to not-lit, not scored as a four-class outcome.')


def main():
    profiles, package = profile_audit.context()  # verifies all 104 frozen inputs
    run = RUN
    audit = profile_audit.inspect_run(run, profiles, package)
    if audit['integrity_errors']:
        raise ValueError(audit['integrity_errors'])
    receipt = json.loads((FREEZE/'freeze.json').read_text())
    frozen_at = datetime.datetime.fromisoformat(receipt['frozen_at']).timestamp()
    baseline = json.loads((run/'baseline.json').read_text())
    record_audit = dict(board=run.name, boot_id=baseline['boot_id'], runtime_fingerprint=audit['runtime_fingerprint'])
    predictions = json.loads((FREEZE/'predictions.json').read_text())
    failures = {r['key']: r for r in json.loads((OUT/'first-failures.json').read_text())}
    audio = {r['key']: r for r in json.loads((OUT/'audio-static.json').read_text())}
    signed = json.loads((SOURCE/'results.json').read_text())
    lit = set(signed['lit_t20_by_screenshot'])
    if set(failures) != {p['key'] for p in predictions}:
        raise ValueError('66-key scope mismatch')
    rows, backgrounds, facts = [], [], []
    for p in predictions:
        key = p['key']; e = failures[key]
        if e['lit'] != (key in lit):
            raise ValueError('image verdict changed since extraction')
        f = record_facts(Path(e['record']), record_audit); facts.append(f)
        if e['record_sha256'] != f['record_sha256']:
            raise ValueError('record changed after extraction')
        grant = 'granted' if f['grant_verified'] is True else 'absent' if f['grant_verified'] is False else 'unknown'
        bg = background_scan(p, grant); backgrounds.append(bg)
        actual = actual_family(e); prior = prior_family(p['prior_wall'])
        known = actual not in {'none-signed-lit','unknown-first-wall','input-identity','input-non-aarch64-elf'}
        causes = [x for x in e['chain'] if 'Caused by:' in x['text']]
        cause = (causes[-1] if causes else e['anchor'])
        terminal = (e.get('first_terminal') or {}).get('anchor')
        terminal_chain = (e.get('first_terminal') or {}).get('chain', [])
        terminal_causes = [x for x in terminal_chain if 'Caused by:' in x['text']]
        terminal_cause = terminal_causes[-1] if terminal_causes else terminal
        terminal_family = actual_family(dict(e, chain=terminal_chain)) if terminal else 'unknown-no-explicit-terminal'
        excluded = list(f['errors'])
        if f['apk_sha256'] != p['apk_sha256']: excluded.append('apk_identity_mismatch')
        if not isinstance(f['clicked_at'], (int,float)) or f['clicked_at'] <= frozen_at:
            excluded.append('not_clicked_after_freeze')
        row = dict(key=key, apk_sha256=f['apk_sha256'], predicted_apk_sha256=p['apk_sha256'],
                   r17o=p['r17o'], r17p=p['r17p'], actual_lit=key in lit,
                   predicted_cause=p['prior_wall'], predicted_family=prior,
                   frozen_b10_static_families=p['b10_static_families'],
                   actual_first_family=actual, first_failure_stage=e['stage'],
                   actual_first_cause=cause['text'] if cause else e['record_error'] or 'unknown',
                   first_failure_evidence=e['log']+':'+str(cause['line']) if cause else e['record'],
                   first_terminal=terminal['text'] if terminal else 'unknown-no-explicit-terminal',
                   actual_terminal_cause=terminal_cause['text'] if terminal_cause else None,
                   actual_terminal_family=terminal_family,
                   terminal_evidence=e['log']+':'+str(terminal['line']) if terminal else None,
                   wall_family_hit=prior==actual if known else None,
                   background_requirement=bg['static_risk'], background_status=bg['status'],
                   grant_verified=f['grant_verified'], audio_static_status=audio[key]['status'],
                   audio_submechanisms=sorted({w['submechanism'] for w in audio[key]['witnesses']}),
                   clicked_at=f['clicked_at'], captured=f['captured_count'],
                   alive_t5=(f['processes']['t5'] or {}).get('alive'),
                   alive_t20=(f['processes']['t20'] or {}).get('alive'),
                   source_record=f['record'], source_record_sha256=f['record_sha256'],
                   hilog_sha256=e.get('log_sha256'),
                   descriptive_eligible=not excluded, exclusions=excluded,
                   same_profile_score_eligible=False)
        rows.append(row)
    eligible = [r for r in rows if r['descriptive_eligible']]
    known = [r for r in eligible if r['wall_family_hit'] is not None]
    terminal_known = [r for r in eligible if not r['actual_lit'] and r['actual_terminal_family'] not in
                      {'unknown-first-wall','unknown-no-explicit-terminal'}]
    groups = []
    for family in sorted({r['actual_first_family'] for r in known}):
        observed = [r for r in known if r['actual_first_family']==family]
        missed = [r for r in observed if not r['wall_family_hit']]
        groups.append(dict(family=family, observed_apps=len(observed),
                           hit_keys=[r['key'] for r in observed if r['wall_family_hit']],
                           missed_keys=[r['key'] for r in missed],
                           meets_two_missed_apps=len(missed)>=2,
                           all_observed_keys=[r['key'] for r in observed],
                           evidence=[r['first_failure_evidence'] for r in observed],
                           treatment='new two-submechanism rule' if family==FAMILY else 'existing family coverage or below threshold'))
    audio_positives = {r['key'] for r in known if r['actual_first_family']==FAMILY}
    audio_alerts = {k for k,a in audio.items() if a['status']=='conditional-reference'}
    totals = dict(records=len(rows), screenshots_captured=sum(f['captured_count'] for f in facts))
    for stage in ('t5','t20'):
        totals['alive_'+stage] = sum((f['processes'][stage] or {}).get('alive',False) for f in facts)
        totals['process_unknown_'+stage] = sum(f['processes'][stage] is None for f in facts)
    results = dict(scope='Offline post-hoc cross-profile calibration; NOT v3 same-profile prospective accuracy',
                   image_authority=str(SOURCE/'results.json'), image_authority_sha256=sha(SOURCE/'results.json'),
                   image_field='lit_t20_by_screenshot', actual_lit=len(lit),
                   freeze_sha256=sha(FREEZE/'freeze.json'), freeze_files_verified=len(receipt['hashes']),
                   profile_audit=audit, actual_state_attestation=signed['state'], counts=totals,
                   all_66_lighting={v:lighting_metric(rows,v) for v in ('r17o','r17p')},
                   eligible_lighting={v:lighting_metric(eligible,v) for v in ('r17o','r17p')},
                   excluded=[dict(key=r['key'],reasons=r['exclusions']) for r in rows if not r['descriptive_eligible']],
                   wall_coverage=dict(diagnosed=len(known), hits=sum(r['wall_family_hit'] for r in known),
                                      misses=sum(not r['wall_family_hit'] for r in known),
                                      unknown_keys=[r['key'] for r in eligible if r['actual_first_family']=='unknown-first-wall'],
                                      policy='Family-level prior_wall coverage, NOT exact-symbol/root-cause accuracy. Bind failure is reported separately from terminal; generic NPEs remain unknown. Runtime-only static hints are not predictions.'),
                   terminal_wall_coverage=dict(diagnosed=len(terminal_known),
                       hits=sum(r['predicted_family']==r['actual_terminal_family'] for r in terminal_known),
                       misses=sum(r['predicted_family']!=r['actual_terminal_family'] for r in terminal_known),
                       policy='Separate first explicit terminal marker; bind failures alone do not count as terminal. See per-key actual_terminal_cause and first-failures.json for nested causes.'),
                   missed_families=groups,
                   audio_calibration=dict(first_wall_keys=sorted(audio_positives),
                       reference_alerts=len(audio_alerts), hits=sorted(audio_positives & audio_alerts),
                       misses=sorted(audio_positives-audio_alerts),
                       unconfirmed_alerts=sorted(audio_alerts-audio_positives),
                       policy='In-sample reference coverage only; 2 different native closure mechanisms, not one fix. Other alerts are latent/unconfirmed, not proven false positives.'),
                   background_scan=dict(status_counts=dict(collections.Counter(b['status'] for b in backgrounds)),
                       static_requirements=sum(b['static_risk'] is True for b in backgrounds),
                       grants_verified=sum(f['grant_verified'] is True for f in facts),
                       policy='Grant read from per-app bundle permission states; satisfied static requirements do not imply success of later stages.'),
                   prediction_update='Original v3 columns immutable; next predictions add conditional audio requirements only. DEX references alone cannot establish startup reachability or library visibility.')
    write(OUT/'results.json',results); write(OUT/'per-key.json',rows)
    write(OUT/'background-static.json',backgrounds); write(OUT/'record-facts.json',facts)
    write(OUT/'missed-walls.json',groups)
    with (OUT/'per-key.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
    print(json.dumps({k:results[k] for k in ['counts','eligible_lighting','wall_coverage','audio_calibration','background_scan']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
