"""Rank static contract candidates separately from actually witnessed blocking."""

import argparse
import base64
import collections
import csv
import gzip
import io
import json
from pathlib import Path

import collect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(path):
    return json.loads(gzip.decompress(base64.b64decode(path.read_bytes())))


def visual_labels():
    old_path=ROOT/'benchmark/2026-10-01-u7-scoring/formal-66/reviews.json'
    new_path=ROOT/'benchmark/2026-10-01-cv2-scoring/outer-signoff.json'
    old=json.loads(old_path.read_text())['rows']
    new=json.loads(new_path.read_text())['keys']
    labels={key:dict(status='lit' if row['visual']=='own-ui' else row['visual'],authority=row['authority'],description=row.get('description')) for key,row in old.items()}
    labels.update({row['key']:dict(status=row['verdict'],authority='ACK(97) 2026-10-01T09:56:21+0800',description=None) for row in new})
    return labels,{str(path.relative_to(ROOT)):collect.digest(path.read_bytes()) for path in [old_path,new_path]}


def theme_contexts(app, site):
    by_name={activity['target']:activity for activity in app['manifest']['activities'] if not activity['alias']}
    output=[]
    for context in site['contexts']:
        activity=by_name.get(context['activity'])
        if activity is not None:
            themed=activity['resolved_theme']
            output.append({**context,'theme':activity['theme'],'theme_name':themed.get('name'),
                           'theme_status':themed['status'],'theme_flags':themed['flags'],
                           'theme_evidence_ref':'facts.json.gz.b64/app='+app['key']+'/activity='+activity['target']+'/resolved_theme',
                           'dynamic_set_theme_present':bool(app['set_theme_calls'])})
    return output


def native_timings(native):
    eager=set()
    delayed=set()
    for identifier,method in native['java']['methods'].items():
        for call in method['native_calls']:
            target=call['owner'].strip('L;')+'.'+call['name']+call['descriptor']
            (eager if '-><init>' in identifier else delayed).add(target)
    return {row['id']:'eager-Java-constructor' if row['id'] in eager else 'non-constructor-native-site; lazy-or-factory' if row['id'] in delayed else 'unknown-Java-native-initiation' for row in native['rows']}


def build(facts, native, labels, calibrations):
    apps=facts['apps']
    if len(apps)!=166 or len({app['key'] for app in apps})!=166 or set(labels)!={app['key'] for app in apps}:
        raise ValueError('Incomplete or mismatched 166-key cohort')
    constructors={row['id']:row for row in native['rows']}
    timings=native_timings(native)
    by_owner=collections.defaultdict(list)
    for identifier,row in constructors.items():
        by_owner['L'+row['owner']+';'].append(identifier)
    rows=[]
    for app in sorted(apps,key=lambda row:row['key']):
        actionbar=[]
        for site in app['actionbar_calls']:
            contexts=theme_contexts(app,site)
            if not contexts and site['library_caller']:
                continue
            actionbar.append({**site,'theme_contexts':contexts,
                'classification':'startup-chain' if any(context['tier']=='startup-chain' for context in contexts) else 'later-activity-lifecycle' if contexts else 'unanchored-reference',
                'theme_contract_candidate':any(context['theme_status']=='no-actionbar-explicit-in-all-local-variants' for context in contexts),
                'limits':'NoActionBar is the correct Android contract, not proof of a crash; U7 violation is observed only in calibrated keys. Later lifecycle can run immediately after splash, before any visible frame.'})
        graphics=[]
        for site in app['graphics_calls']:
            matches=by_owner.get(site['owner'],[])
            if site['name'].startswith('native'):
                direct=site['owner'].strip('L;')+'.'+site['name']+site['descriptor']
                matches=[direct] if direct in constructors else []
            if not matches:
                continue
            compact_site={key:site[key] for key in ['method','dex','owner','name','descriptor','line','offset','instruction']}
            compact_site['contexts']=[{key:context[key] for key in ['activity','tier','conditional']} for context in site['contexts']]
            compact_site['full_call_path_ref']='facts.json.gz.b64/app='+app['key']+'/graphics_call='+site['dex']+':'+str(site['line'])
            graphics.append({**compact_site,'native_ids':matches,
                'native_initiation':{identifier:timings[identifier] for identifier in matches},
                'classification':'startup-chain' if any(context['tier']=='startup-chain' for context in site['contexts']) else 'later-activity-lifecycle' if site['contexts'] else 'unanchored-reference',
                'limits':'Shader/ColorFilter construction can precede native creation until first drawing; exact arguments, error handling and actual invocation remain unknown'})
        rows.append(dict(key=app['key'],package=app['package'],apk_sha256=app['apk_sha256'],cohort=app['cohort'],
            signed_t20=labels[app['key']],actionbar=actionbar,graphics=graphics,calibration=calibrations.get(app['key']),
            dex_count=len(app['dex']),reachability=app['reachability']))
    startup=[]
    later=[]
    unanchored=[]
    for row in rows:
        candidates=[site for site in row['actionbar'] if site['theme_contract_candidate']]
        if any(site['classification']=='startup-chain' for site in candidates):
            startup.append(row['key'])
        if any(site['classification']=='later-activity-lifecycle' for site in candidates):
            later.append(row['key'])
        if any(site['classification']=='unanchored-reference' for site in row['actionbar']):
            unanchored.append(row['key'])
    ranks=[]
    for identifier,constructor in constructors.items():
        consumers=[]
        startup_consumers=[]
        later_consumers=[]
        for row in rows:
            sites=[site for site in row['graphics'] if identifier in site['native_ids']]
            if sites:
                consumers.append(row['key'])
            if any(site['classification']=='startup-chain' for site in sites):
                startup_consumers.append(row['key'])
            if any(site['classification']=='later-activity-lifecycle' for site in sites):
                later_consumers.append(row['key'])
        unconditional=any(implementation.get('throw',{}).get('status')=='unconditional-normal-path-direct-throw' for implementation in constructor['implementations'])
        confirmed=[key for key,calibration in calibrations.items() if calibration.get('native_id')==identifier]
        ranks.append(dict(id=identifier,jni_status=constructor['jni_status'],native_initiation=timings[identifier],
            observed_blocked_keys=confirmed,observed_blocked_count=len(confirmed),
            unconditional_throw_callsite_upper_bound=len(consumers) if unconditional else 0,
            predicted_block_if_invoked=unconditional,consumer_count=len(consumers),consumer_keys=consumers,
            startup_candidate_keys=startup_consumers,later_activity_candidate_keys=later_consumers,
            implementation_throw_statuses=sorted({implementation.get('throw',{}).get('status','unknown') for implementation in constructor['implementations']}),
            argument_and_reachability='unknown; counts are unique-key references, not measured deaths/unlocks'))
    ranks.sort(key=lambda row:(-row['observed_blocked_count'],-row['unconditional_throw_callsite_upper_bound'],-row['consumer_count'],row['id']))
    ranked_themes=dict(cluster='appcompat-actionbar-theme',startup_chain_candidates=startup,later_activity_candidates=later,
        later_signed_lit_candidates=[row['key'] for row in rows if row['key'] in later and row['signed_t20']['status']=='lit'],
        unanchored_references=unanchored,
        observed_first_content_failures=[key for key,value in calibrations.items() if value['cluster']=='appcompat-actionbar-theme'],
        timing_limits='Static startup and later-Activity tiers are not stopwatch ordering. Known Memory/Yahtzee failures are separately calibrated; lit later candidates remain risks, not guaranteed post-frame deaths.')
    primary_startup=sorted(set(startup)|set(ranked_themes['observed_first_content_failures']))
    primary_later=sorted(set(later)-set(primary_startup))
    ranked_themes['two_tier_schedule']=dict(startup_or_calibrated_first_content=primary_startup,later_activity_only=primary_later,
        later_only_signed_lit=[row['key'] for row in rows if row['key'] in primary_later and row['signed_t20']['status']=='lit'],
        scope_overlap_keys=sorted(set(startup)&set(later)),
        limits='Mutually exclusive triage order; calibrated first-content failures are distinguished from static startup witnesses. Later Activity is a candidate, not a proven timestamp after t20.')
    for row in rows:
        row['actionbar_schedule']='startup-or-calibrated-first-content' if row['key'] in primary_startup else 'later-activity-only' if row['key'] in primary_later else 'unanchored-or-theme-unknown' if row['actionbar'] else 'no-literal-API-witness'
    hashes=collections.defaultdict(list)
    for app in apps:
        hashes[app['apk_sha256']].append(app['key'])
    packages=collections.defaultdict(list)
    for app in apps:
        packages[app['package']].append(app['key'])
    return dict(schema='b10-theme-graphics-predictions-v1',baseline='identity-pinned U7; no N10/J8/T7e',rows=rows,
        actionbar_cluster=ranked_themes,graphics_ranked=ranks,counts=dict(keys=166,unique_apk_sha=len(hashes),unique_packages=len(packages),
            actionbar_app_refs=sum(bool(row['actionbar']) for row in rows),graphics_constructor_app_refs=sum(bool(row['graphics']) for row in rows),
            startup_theme_candidates=len(startup),later_theme_candidates=len(later),later_theme_signed_lit=len(ranked_themes['later_signed_lit_candidates']),
            primary_startup=len(primary_startup),primary_later=len(primary_later),primary_later_signed_lit=len(ranked_themes['two_tier_schedule']['later_only_signed_lit'])),
        duplicated_apk_identities={pin:keys for pin,keys in hashes.items() if len(keys)>1},
        duplicate_package_keys={name:keys for name,keys in packages.items() if len(keys)>1},
        prediction_limits='All walls conditional except compiled unconditional throw if invoked; known failures are calibrations. Absent literal API call never proves no obfuscated/dynamic use.')


def generate():
    facts=load(HERE/'facts.json.gz.b64')
    native=json.loads((HERE/'native-constructors.json').read_text())
    labels,pins=visual_labels()
    calibrations=json.loads((HERE/'calibrations.json').read_text())['keys']
    for relative,pin in {**facts['scanner_dependencies'],**native['audit_dependencies']}.items():
        if collect.digest((ROOT/relative).read_bytes())!=pin:
            raise ValueError('Scanner dependency drift: '+relative)
    result=build(facts,native,labels,calibrations)
    result['source']=dict(facts_sha256=collect.digest((HERE/'facts.json.gz.b64').read_bytes()),
        native_audit_sha256=collect.digest((HERE/'native-constructors.json').read_bytes()),
        calibrations_sha256=collect.digest((HERE/'calibrations.json').read_bytes()),visual_pins=pins,
        generator_sha256=collect.digest(Path(__file__).read_bytes()))
    return result


def csv_text(result):
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,['key','package','apk_sha256','signed_t20','actionbar_schedule','startup_actionbar_theme','later_actionbar_theme','unanchored_actionbar','graphics_constructor_ids','calibration'],lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        writer.writerow(dict(key=row['key'],package=row['package'],apk_sha256=row['apk_sha256'],signed_t20=row['signed_t20']['status'],actionbar_schedule=row['actionbar_schedule'],
            startup_actionbar_theme=sum(site['classification']=='startup-chain' and site['theme_contract_candidate'] for site in row['actionbar']),
            later_actionbar_theme=sum(site['classification']=='later-activity-lifecycle' and site['theme_contract_candidate'] for site in row['actionbar']),
            unanchored_actionbar=sum(site['classification']=='unanchored-reference' for site in row['actionbar']),
            graphics_constructor_ids=';'.join(sorted({identifier for site in row['graphics'] for identifier in site['native_ids']})),
            calibration=(row['calibration'] or {}).get('cluster','none')))
    return stream.getvalue()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=generate()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    (args.output/'PREDICTIONS.csv').write_text(csv_text(result))
    print(result['counts'])


if __name__=='__main__':
    main()
