"""Join registration evidence and native exposure without promoting references to deaths."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(row, reference):
    if row['AOSP14r1']:
        return 'exact-AOSP14r1-entrypoint'
    if not row['function'].startswith('register_android_'):
        return 'outside-register_android-context'
    if row['function'] in reference.get('outer_full_tree_absence_attestation', {}):
        return 'Westlake-custom-name-absent-in-AOSP14r1'
    return 'unknown-reference-entrypoint'


def relationship(symbol):
    if symbol == 'AAssetManager_fromJava':
        return 'AssetManager registration; runtime and libandroid cache owners are distinct', 'duplicate-owner-static-risk; actual caller/provider unresolved'
    if symbol == 'ANativeWindow_fromSurface':
        return 'Surface registration; compatibility converter is not automatically the AOSP cached implementation', 'no-proven-skipped-cache; namespace and window routing unknown'
    if symbol.startswith('AndroidBitmap_'):
        return 'Graphics/Bitmap whole-function delegation; external GraphicsJNI VM initialization is separate', 'external-VM-context-gap; API provider outside three-owner inventory unknown'
    if symbol == 'AHardwareBuffer_fromHardwareBuffer':
        return 'HardwareBuffer original JNI cache registration is outside the 95-entry inventory', 'public-converter-not-found-in-three-owners; other-provider unknown'
    if symbol.startswith(('AAsset_', 'AAssetManager_', 'AConfiguration_')):
        return 'NDK native object API; Java converter cache is only a prerequisite if that path is used', 'reference-only; no registration-side-effect death established'
    return 'Exact native API reference; no automatic dependency on a Java registration cache', 'reference-only; provider and execution unknown'


def join(audit, consumers, reference, signoff):
    apps = consumers['apps']
    signed_rows = signoff['keys']
    observed = {row['key']:row for row in signed_rows} if isinstance(signed_rows,list) else signed_rows
    if len(observed) != len(signed_rows):
        raise ValueError('Duplicate signoff key')
    if len(apps) != 166 or len({row['key'] for row in apps}) != 166 or set(observed) != {row['key'] for row in apps}:
        raise ValueError('Signoff/native cohort mismatch')
    if audit['entries'] != len(audit['rows']) or not audit['reference_verified'] or audit['identity']['exit'] != 0:
        raise ValueError('Unverified registration identity/reference')
    for row in audit['rows']:
        row['reference_comparison'] = classify(row, reference)
        row['original_cache_identifier_difference_is_causal'] = False
    for app in apps:
        app['U8_signed_t20'] = observed[app['key']]['verdict']
    for group in consumers['API_groups']:
        group['U8_lit_keys'] = [key for key in group['keys'] if observed[key]['verdict'] == 'lit']
        group['U8_lit_count'] = len(group['U8_lit_keys'])
        group['registration_context'], group['gap_status'] = relationship(group['symbol'])
        group['predicted_unlock_count'] = None
    counts = Counter(row['reference_comparison'] for row in audit['rows'])
    headers = Counter(library['header'] for app in apps for library in app['libraries'])
    summary = dict(schema='b10-registration-impact-v1',keys=166,registration_entries=audit['entries'],
        unique_registration_functions=len({row['function'] for row in audit['rows']}),
        android_registration_entries=sum(row['function'].startswith('register_android_') for row in audit['rows']),
        comparison_counts=dict(counts),dispatch_tables=dict(Counter(row['table'] for row in audit['rows'])),
        reference_files=reference['files_count'],reference_frameworks_base_commit=reference['frameworks_base_commit'],
        exact_identifier_difference_modules=sum(bool(row['original_cache_identifiers_not_written_in_ported_body']) for row in audit['rows']),
        cache_owner_symbols=len(audit['cache_owners']),libraries=consumers['libraries'],headers=dict(headers),
        native_API_exposed_keys=len(consumers['keys_with_API_exposure']),API_groups=len(consumers['API_groups']),
        missing_sidecar_keys=consumers['missing_sidecar_keys'],U8_signed_states=dict(Counter(value['verdict'] for value in observed.values())),
        proven_registration_side_effect_deaths=0,predicted_unlock_count=None,
        limitations=['Exposure is not execution; no ABI-invalid member is marked clean',
            'Whole-function registration preserves in-body initializers if the call succeeds; exported symbols do not attest execution',
            'Renamed, helper-based and deferred caches cannot be diagnosed from lexical identifier differences',
            'U8 ath0-rpn first fatal is Skia dumpMemoryStatistics, not a Typeface VM frame',
            'U8 glmark2 first fatal is GetLongField from app native_getSceneInfo; AssetManager owner linkage is unresolved'])
    return summary


def write_csv(path, fields, rows):
    with path.open('w',newline='') as output:
        writer = csv.DictWriter(output,fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key:json.dumps(value,sort_keys=True) if isinstance(value,(list,dict)) else value for key,value in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['audit','consumers','reference','signoff']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    audit,consumers,reference,signoff = [json.loads(getattr(args,name).read_text()) for name in ['audit','consumers','reference','signoff']]
    summary = join(audit,consumers,reference,signoff)
    summary['input_sha256'] = {name:sha(getattr(args,name)) for name in ['audit','consumers','reference','signoff']}
    summary['report_sha256'] = sha(Path(__file__))
    args.output.mkdir(parents=True,exist_ok=True)
    for name,value in [('REGISTRATIONS.json',audit),('CONSUMERS.json',consumers),('reference.json',reference),('results.json',summary)]:
        (args.output/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    rows = []
    for row in audit['rows']:
        rows.append(dict(function=row['function'],table=row['table'],mode=row['mode'],dispatch_line=row['line'],comparison=row['reference_comparison'],
            original=[f"{value['file']}:{value['first_line']}" for value in row['AOSP14r1']],
            ported=[f"{value['file']}:{value['first_line']}" for value in row['ported_source_candidates']],
            provider_symbols=row['provider_symbols'],identifier_difference=row['original_cache_identifiers_not_written_in_ported_body'],causal=False))
    write_csv(args.output/'REGISTRATIONS.csv',list(rows[0]),rows)
    rows = [dict(symbol=row['symbol'],affected_keys=row['affected_keys'],keys=row['keys'],U8_lit_count=row['U8_lit_count'],
        U8_lit_keys=row['U8_lit_keys'],evidence_kinds=sorted({item['kind'] for item in row['evidence']}),
        registration_context=row['registration_context'],gap_status=row['gap_status'],predicted_unlock_count='unknown',causal=False) for row in consumers['API_groups']]
    write_csv(args.output/'API-IMPACT.csv',list(rows[0]),rows)
    rows = [dict(key=app['key'],package=app['package'],apk_sha256=app['apk_sha256'],libraries=len(app['libraries']),
        AArch64_libraries=sum(row['header']=='valid-ELF64-AArch64' for row in app['libraries']),
        API_symbols=sorted({item['symbol'] for library in app['libraries'] for item in library['API_evidence']}),
        missing_sidecars=app['missing_sidecars'],U8_signed_t20=app['U8_signed_t20'],execution_proved=False) for app in consumers['apps']]
    write_csv(args.output/'CONSUMERS.csv',list(rows[0]),rows)
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':
    main()
