"""Summarize PID-bound BitVector observations without assigning a causal crash."""

import argparse
import base64
from collections import defaultdict
import gzip
import importlib.util
import json
from pathlib import Path

REPORT_SPEC = importlib.util.spec_from_file_location('b10_libart_report',Path(__file__).with_name('report.py'))
report = importlib.util.module_from_spec(REPORT_SPEC)
REPORT_SPEC.loader.exec_module(report)


def summarize(facts):
    if facts['mode'] != 'completed-sequential-U8' or not facts['coverage']['full'] or facts['coverage']['unobserved_keys']:
        raise ValueError('Incomplete BitVector facts')
    if len(facts['rows']) != 166 or len({row['key'] for row in facts['rows']}) != 166:
        raise ValueError('Incomplete/duplicate BitVector cohort')
    rows = []
    classes = defaultdict(lambda: dict(keys=set(), observations=0, suspected_keys=set(), no_terminal_keys=set()))
    for entry in facts['rows']:
        bits = entry['bits'] or {}
        fatal = entry['fatal'] or {}
        correlation = entry['correlation']
        root = fatal.get('root') or {}
        event = root.get('event') or {}
        positive = bits.get('positive', [])
        before = correlation['before_first_terminal'] if 'before_first_terminal' in correlation else []
        names = sorted({item['class_name'] for item in positive if item['class_name']})
        row = dict(key=entry['key'], source=entry['source'], probe_status=entry['probe_status'], status=entry['status'],
            target_pids=entry.get('target_pids', []), positive_observations=len(positive), positive_class_count=len(names), positive_class_examples=names[:8],
            full_class_inventory='bitvector-facts.json.gz.b64:rows/'+entry['key']+'/bits/positive',
            zero_observations=len(bits.get('zero', [])), foreign_pid_observations_excluded=bits.get('foreign_pid_lines_excluded', 0),
            fatal_status=fatal.get('status', 'unknown-no-log'), first_terminal_kind=(fatal.get('terminal') or {}).get('kind'),
            root_status=root.get('status'), root_method=root.get('method'), root_message=event.get('message', root.get('message', '')),
            root_line=event.get('line'), before_first_terminal=len(before), correlation=correlation['status'], causal=False,
            hilog_sha256=(entry.get('binding') or {}).get('hilog_sha256'), signed_U8_t20='unknown-await-outer-signoff')
        rows.append(row)
        for observation in positive:
            name = observation['class_name'] or '<unknown-class>'
            cluster = classes[name]
            cluster['keys'].add(entry['key'])
            cluster['observations'] += 1
            if correlation['status'].startswith('suspected-'):
                cluster['suspected_keys'].add(entry['key'])
            if fatal.get('status') == 'no-observed-termination':
                cluster['no_terminal_keys'].add(entry['key'])
    clusters = [dict(class_name=name, affected_keys=len(value['keys']), keys=sorted(value['keys']), observations=value['observations'],
        suspected_keys=sorted(value['suspected_keys']), no_terminal_keys=sorted(value['no_terminal_keys']), causal=False) for name,value in classes.items()]
    clusters.sort(key=lambda item:(-item['affected_keys'], item['class_name']))
    return dict(schema='b10-libart-bitvector-impact-v1', keys=len(rows), apps=rows, positive_class_clusters=clusters,
        positive_keys=[row['key'] for row in rows if row['positive_observations']], suspected_victim_keys=[row['key'] for row in rows if row['correlation'].startswith('suspected-')],
        positive_no_observed_terminal_keys=[row['key'] for row in rows if row['positive_observations'] and row['fatal_status']=='no-observed-termination'],
        positive_observations=sum(row['positive_observations'] for row in rows), zero_observations=sum(row['zero_observations'] for row in rows),
        coverage=facts['coverage'], correlation_counts=facts['counts'], selected_roots=facts['selected_roots'], state=facts['state'],
        input_identity_csv_sha256=facts['input_identity_csv_sha256'], scanner_dependencies=facts['dependencies'],
        limits=['Positive bits alone do not prove the fatal root; every causal verdict remains false',
            'A positive alive process is not proof of a lit screenshot; U8 screenshot signoff is separate',
            'No positive observation is not proof of a clean class or runtime', 'Zero observations and foreign PID observations never enter a suspected victim cluster'])


def compact(facts, input_sha):
    names = sorted({item['class_name'] for row in facts['rows'] for group in ['positive','zero'] for item in (row['bits'] or {}).get(group,[]) if item['class_name']})
    indexes = {name:index for index,name in enumerate(names)}
    rows = []
    for row in facts['rows']:
        selected = dict(row)
        if row['bits'] is not None:
            source = row['bits']
            selected['bits'] = dict(foreign_pid_lines_excluded=source['foreign_pid_lines_excluded'], unknown_class_positive=len(source['unknown_class_positive']))
            for group in ['positive','zero']:
                selected['bits'][group] = [[item['event']['line'], item['event']['timestamp'], item['event']['pid'], item['event']['tid'], indexes.get(item['class_name']), item['garbage_set_bits']] for item in source[group]]
                selected['bits'][group+'_example'] = source[group][0] if source[group] else None
        selected['correlation'] = {name:[[item['event']['pid'],item['event']['line']] for item in value] if name in {'before_first_terminal','class_linked_evidence'} else value for name,value in row['correlation'].items()}
        rows.append(selected)
    return dict({name:value for name,value in facts.items() if name!='rows'}, rows=rows, classes=names,
        source_verbose_scan_sha256=input_sha, representation='Lossless observation coordinates and bit/class values; complete original messages recoverable from SHA-pinned hilog source:line',
        observation_fields=['line','timestamp','pid','tid','class_index_or_null','garbageSetBits'], correlation_coordinate_fields=['pid','line'])


def bind_signoff(result, payload):
    signed = json.loads(payload)
    labels = {row['key']:row for row in signed['keys']}
    allowed = {'lit','lit-webview-fallback','alive-launcher-foreground','alive-white-window','alive-black-window','alive-blank-window','dead','app_failed'}
    if signed['schema'] != 'outer-signoff-v1' or signed['state'].get('name') != 'U8' or any(signed['state'].get(field)!=pin for field,pin in result['state'].items()):
        raise ValueError('Wrong signed U8 state')
    if len(signed['keys']) != 166 or len(labels)!=166 or set(labels)!={row['key'] for row in result['apps']} or set(signed['runs'])!=set(result['selected_roots']):
        raise ValueError('Incomplete/duplicate or different signed U8 attempts')
    for row in result['apps']:
        label = labels[row['key']]
        if label['verdict'] not in allowed or label['run'] not in Path(row['source']).parts:
            raise ValueError('Unknown verdict or mismatched signed attempt')
        row['signed_U8_t20'] = label['verdict']
    result['signoff_sha256'] = report.sha(payload)
    result['positive_signed_lit_keys'] = [row['key'] for row in result['apps'] if row['positive_observations'] and row['signed_U8_t20']=='lit']
    result['positive_signed_unlit_keys'] = [row['key'] for row in result['apps'] if row['positive_observations'] and row['signed_U8_t20'] not in {'lit','lit-webview-fallback'}]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--signoff', type=Path)
    args = parser.parse_args()
    payload = args.facts.read_bytes()
    facts = json.loads(payload)
    result = summarize(facts)
    if args.signoff:
        bind_signoff(result,args.signoff.read_bytes())
    compact_payload = (json.dumps(compact(facts,report.sha(payload)),sort_keys=True)+'\n').encode()
    result['facts_sha256'] = report.sha(compact_payload)
    result['verbose_scan_sha256'] = report.sha(payload)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'bitvector-facts.json.gz.b64').write_text(base64.b64encode(gzip.compress(compact_payload,mtime=0)).decode()+'\n')
    cluster_payload = (json.dumps(result.pop('positive_class_clusters'),sort_keys=True)+'\n').encode()
    (args.output/'BITVECTOR-CLUSTERS.json.gz.b64').write_text(base64.b64encode(gzip.compress(cluster_payload,mtime=0)).decode()+'\n')
    result['positive_class_clusters'] = dict(file='BITVECTOR-CLUSTERS.json.gz.b64',decoded_sha256=report.sha(cluster_payload),rows=len(json.loads(cluster_payload)))
    (args.output/'BITVECTOR.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    (args.output/'BITVECTOR.csv').write_text(report.csv_text(result['apps']))
    print(json.dumps({name:result[name] for name in ['keys','positive_keys','suspected_victim_keys','positive_no_observed_terminal_keys','positive_observations','zero_observations']},sort_keys=True))


if __name__ == '__main__':
    main()
