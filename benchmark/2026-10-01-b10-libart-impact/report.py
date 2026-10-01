"""Compact exact-class exposure facts without converting references into fatal predictions."""

import argparse
import base64
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TIERS = ['startup-chain-candidate', 'startup-or-later-transition-candidate', 'later-component-candidate', 'unanchored-not-proved-later']


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def summarize(facts):
    baseline = list(csv.DictReader(io.StringIO((ROOT/'benchmark/2026-10-01-b10-theme-graphics/PREDICTIONS.csv').read_text())))
    priors = {row['key']:row for row in baseline}
    apps = facts['apps']
    if len(apps) != 166 or len({app['key'] for app in apps}) != 166 or {app['key'] for app in apps} != set(priors):
        raise ValueError('Incomplete/duplicate static 166 cohort')
    rows = []
    clusters = defaultdict(lambda:dict(keys=[], tiers=defaultdict(list), examples=[], roles=Counter(), previously_lit=[]))
    for app in sorted(apps, key=lambda item:item['key']):
        if any(app[field] != priors[app['key']][field] for field in ['package','apk_sha256']):
            raise ValueError('Static APK/package cross-check mismatch')
        by_tier = {tier:set() for tier in TIERS}
        for site in app['sites']:
            by_tier[site['tier']].update(site['missing'])
        selected = set()
        primary = {}
        for tier in TIERS:
            primary[tier] = sorted(by_tier[tier]-selected)
            selected.update(primary[tier])
        primary[TIERS[-1]] = sorted(set(primary[TIERS[-1]]) | (set(app['absent_boot_and_app'])-selected))
        row = dict(key=app['key'], package=app['package'], apk_sha256=app['apk_sha256'], dex_count=len(app['dex']),
            absent_boot_and_app_count=len(app['absent_boot_and_app']), startup_candidate_classes=primary[TIERS[0]],
            transition_timing_unknown_classes=primary[TIERS[1]], later_component_only_in_static_graph_classes=primary[TIERS[2]],
            unanchored_or_pool_only_classes=primary[TIERS[3]], runtime_jar_only_classes=app['runtime_jar_only'],
            type_pool_only_without_site=app['type_pool_only_without_site'], site_tiers=app['site_tiers'],
            prior_signed_t20=priors[app['key']]['signed_t20'], prior_signoff_source='cv2' if app['key'].startswith('cv2-') else 'U7', semantic_limit='Reference absence and conditional staged RTA are not proof of eager parsing, first-frame order or fatal failure')
        row['reachability_budget_truncated'] = app['reachability']['budget_truncated']
        rows.append(row)
        for missing in app['absent_boot_and_app']:
            cluster = clusters[missing]
            cluster['keys'].append(app['key'])
            cluster['runtime_jar_provided'] = missing in app['runtime_jar_only']
            tier = next(tier for tier in TIERS if missing in primary[tier])
            cluster['tiers'][tier].append(app['key'])
            if priors[app['key']]['signed_t20'] in {'lit','lit-webview-fallback'}:
                cluster['previously_lit'].append(app['key'])
            sites = [site for site in app['sites'] if missing in site['missing']]
            for site in sites:
                role = 'referenced-member-owner' if site['reference'].startswith(missing+'->') else 'member-signature-type' if '->' in site['reference'] else site['kind']
                cluster['roles'][role] += 1
            for tier in TIERS:
                match = next((site for site in sites if site['tier']==tier), None)
                if match:
                    cluster['examples'].append(dict(key=app['key'], **match))
    class_rows = [dict(class_name=name, affected_keys=len(value['keys']), keys=sorted(value['keys']), primary_tiers={tier:sorted(keys) for tier,keys in value['tiers'].items()},
        runtime_jar_provided=value['runtime_jar_provided'], roles=dict(value['roles']), previously_lit_keys=sorted(value['previously_lit']),
        examples=value['examples'], causal_claim=False) for name,value in clusters.items()]
    class_rows.sort(key=lambda row:(-row['affected_keys'],row['class_name']))
    return dict(schema='b10-libart-class-impact-v1', keys=166, dex=sum(len(app['dex']) for app in apps),
        boot_classes=facts['boot_classes'], auxiliary_runtime_classes=facts['auxiliary_classes'], absent_distinct_classes=len(class_rows),
        apps=rows, class_clusters=class_rows, site_tiers=dict(sum((Counter(app['site_tiers']) for app in apps),Counter())),
        key_groups={tier:sorted(row['key'] for row in rows if any(cluster['primary_tiers'].get(tier) and row['key'] in cluster['primary_tiers'][tier] for cluster in class_rows)) for tier in TIERS},
        identity=facts['identity'], scanner_dependencies=facts['scanner_dependencies'], tool_sha256=facts['tools'],
        reachability_budget_truncated_keys=sorted(app['key'] for app in apps if app['reachability']['budget_truncated']),
        limits=['Do not add missing hidden classes merely from this inventory; packlist on Android shows lazy resolution can be correct',
            'Later-only means only in this static component graph, not proved after t20', 'No-frame and unknown reflection/loader exposure stay unanchored',
            'Classes supplied by the separate runtime jar are not automatically reachable from every app loader', 'Affected count is referenced-key count, not expected unlock count'])


def csv_text(rows):
    stream = io.StringIO()
    fields = list(rows[0])
    writer = csv.DictWriter(stream, fields, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({name:';'.join(map(str,value)) if isinstance(value,list) else json.dumps(value,sort_keys=True) if isinstance(value,dict) else value for name,value in row.items()})
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    payload = args.facts.read_bytes()
    facts = json.loads(payload)
    result = summarize(facts)
    result['facts_sha256'] = sha(payload)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'class-facts.json.gz.b64').write_text(base64.b64encode(gzip.compress(payload,mtime=0)).decode()+'\n')
    cluster_payload = (json.dumps(result['class_clusters'],sort_keys=True)+'\n').encode()
    (args.output/'CLASS-CLUSTERS.json.gz.b64').write_text(base64.b64encode(gzip.compress(cluster_payload,mtime=0)).decode()+'\n')
    summary = {key:value for key,value in result.items() if key!='class_clusters'}
    summary['class_clusters'] = dict(file='CLASS-CLUSTERS.json.gz.b64', decoded_sha256=sha(cluster_payload), rows=len(result['class_clusters']))
    (args.output/'MISSING-CLASSES.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    (args.output/'MISSING-CLASSES.csv').write_text(csv_text(result['apps']))
    (args.output/'identity.json').write_text(json.dumps(facts['identity'],sort_keys=True,indent=2)+'\n')
    (args.output/'PACKLIST.json').write_text(json.dumps(next(row for row in result['class_clusters'] if row['class_name']=='Lcom/android/internal/util/Predicate;'),sort_keys=True,indent=2)+'\n')
    print(json.dumps({field:result[field] for field in ['keys','dex','boot_classes','absent_distinct_classes','site_tiers']},sort_keys=True))


if __name__=='__main__':
    main()
