"""One-entry three-freeze visual scorer with honest diagnostic and replay boundaries."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts/lab'))
import first_fatal

VERDICTS = ['lit', 'lit-webview-fallback', 'alive-launcher-foreground', 'alive-blank-window', 'dead', 'app_failed']
OWN_UI = {'lit', 'lit-webview-fallback'}
U8_STATE = {'RUNTIME':'e953c0921536', 'BOOTIMAGE':'4db882a81732'}
BASELINE_STATE = {'RUNTIME':'68b7fb016253', 'BOOTIMAGE':'8fe2e5fd7d65'}
PINS = {
    'cv2': ('benchmark/2026-10-01-corpus-v2/apk-scan-v1/PREDICTIONS.csv', 'ab51ab2df4fa6d8e66989d8713da71b79ef5e9c9e6b473f6c54a4bd1d1bc21b1', 100),
    'actionbar': ('benchmark/2026-10-01-b10-theme-graphics/PREDICTIONS.csv', 'c115d17cd826c479c2f549b2b9e0e92825a4029cab1383079fe601276add12bd', 166),
    'webview': ('benchmark/2026-10-01-webview-startup-prediction/PREDICTIONS.csv', '94d701664e337bd6f4c1544704927a60a331d0b6a4dcffae3fbfce1f7e08e66b', 7),
}
OLD_REVIEWS = 'benchmark/2026-10-01-u7-scoring/formal-66/reviews.json'
OLD_SHA = '8ccaa122f1dced1e7f2a87e8e12f1439b8ea16867dc8828951dbb10a73552c63'
CV2_BASELINE = 'benchmark/2026-10-01-cv2-scoring/outer-signoff.json'
CV2_SHAS = {'7a90099dde7be440513b979f02d37259d941a7dfcf14187ef961d8ec20c82d84', '01a25763077dff2d57e1cb90d8d8480c417efe7578be1b0509e3129592a42cf1'}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def indexed(rows, count):
    output = {row['key']:row for row in rows}
    if len(rows) != count or len(output) != count:
        raise ValueError('Incomplete or duplicate key cohort')
    return output


def parse_prediction(payload, pin, count):
    if digest(payload) != pin:
        raise ValueError('Frozen prediction SHA mismatch')
    return indexed(list(csv.DictReader(io.StringIO(payload.decode()))), count)


def predictions():
    output = {name:parse_prediction((ROOT/path).read_bytes(), pin, count) for name,(path,pin,count) in PINS.items()}
    all_keys = set(output['actionbar'])
    for name in ['cv2','webview']:
        if not set(output[name]) <= all_keys:
            raise ValueError('Prediction cohort not contained in 166 keys')
        for key, row in output[name].items():
            parent = output['actionbar'][key]
            if any(row[field] != parent[field] for field in ['package','apk_sha256']):
                raise ValueError('Cross-freeze APK/package mismatch: '+key)
    return output


def signoff(data, keys, expected_state):
    if data.get('schema') != 'outer-signoff-v1' or not data.get('signed_by') or not data.get('board_entry'):
        raise ValueError('Missing outer signoff authority/schema')
    rows = indexed(data.get('keys', []), len(keys))
    if set(rows) != set(keys):
        raise ValueError('Wrong signed key set')
    if any(row.get('verdict') not in VERDICTS for row in rows.values()):
        raise ValueError('Invalid visual verdict')
    if any(data.get('state',{}).get(field) != pin for field,pin in expected_state.items()):
        raise ValueError('Wrong runtime/boot state')
    actual = Counter(row['verdict'] for row in rows.values())
    declared = data.get('counts')
    if not isinstance(declared,dict) or any(type(value) is not int or value < 0 for value in declared.values()):
        raise ValueError('Invalid declared verdict totals')
    if set(declared)-set(VERDICTS) or Counter(declared) != actual:
        raise ValueError('Signed counts do not match rows')
    if data.get('strict_lit',actual['lit']) != actual['lit'] or data.get('own_ui_incl_fallback',sum(actual[label] for label in OWN_UI)) != sum(actual[label] for label in OWN_UI):
        raise ValueError('Signed lit totals do not match rows')
    return rows


def baselines(frozen):
    old_payload = (ROOT/OLD_REVIEWS).read_bytes()
    cv2_payload = (ROOT/CV2_BASELINE).read_bytes()
    if digest(old_payload) != OLD_SHA or digest(cv2_payload) not in CV2_SHAS:
        raise ValueError('Signed U7 baseline SHA drift')
    old = json.loads(old_payload)['rows']
    if len(old) != 66 or set(old) != set(frozen['actionbar'])-set(frozen['cv2']):
        raise ValueError('Old 66 baseline cohort mismatch')
    cv2_data = json.loads(cv2_payload)
    cv2 = signoff(cv2_data, frozen['cv2'], BASELINE_STATE)
    output = {}
    for key,row in old.items():
        output[key] = dict(visual=row['visual'], own_ui=row['visual']=='own-ui', functional=None,
            authority=row['authority'], source=OLD_REVIEWS, description=row.get('description'),
            limits='U7 reviews sign app-owned screen, not a six-class functional-WebView verdict; desktop does not prove death')
    for key,row in cv2.items():
        output[key] = dict(visual=row['verdict'], own_ui=row['verdict'] in OWN_UI, functional=row['verdict']=='lit',
            authority=cv2_data['board_entry'], source=CV2_BASELINE,
            limits='cv2 U7 visual baseline; fallback is separately classified')
    for key,row in output.items():
        if frozen['actionbar'][key]['signed_t20'] != ('lit' if row['visual']=='own-ui' else row['visual']):
            raise ValueError('B10 prior signed label mismatch: '+key)
    return output, {OLD_REVIEWS:digest(old_payload), CV2_BASELINE:digest(cv2_payload)}


def changes(frozen, prior, observed):
    rows = []
    for key in sorted(frozen['actionbar']):
        before = prior[key]
        after = observed.get(key)
        own_ui = after['verdict'] in OWN_UI if after else None
        change = 'unobserved' if after is None else 'new-lit' if own_ui and not before['own_ui'] else 'regression' if before['own_ui'] and not own_ui else 'unchanged'
        functional_change = 'unknown-old-coarse-or-unobserved'
        if after is not None and before['functional'] is not None:
            functional = after['verdict']=='lit'
            functional_change = 'upgrade' if functional and not before['functional'] else 'regression' if before['functional'] and not functional else 'unchanged'
        rows.append(dict(key=key,package=frozen['actionbar'][key]['package'],apk_sha256=frozen['actionbar'][key]['apk_sha256'],
            baseline_visual=before['visual'], baseline_own_ui=before['own_ui'], baseline_authority=before['authority'], baseline_source=before['source'],
            observed_t20=after['verdict'] if after else None, board=after.get('board') if after else None,
            own_ui_change=change, functional_change=functional_change,
            raw_visual_changed=None if after is None or before['functional'] is None else before['visual'] != after['verdict'],
            limits='Key-based signed visual comparison; baseline coarse labels and actual per-run input identity stay separate'))
    return dict(rows=rows, own_ui_counts=dict(Counter(row['own_ui_change'] for row in rows)),
                functional_counts=dict(Counter(row['functional_change'] for row in rows)))


def matrix(predicted_labels, rows, predicted_field):
    output = {label:{verdict:0 for verdict in VERDICTS} for label in predicted_labels}
    unobserved = Counter()
    for row in rows:
        label = row[predicted_field]
        if label not in output:
            raise ValueError('Invalid frozen prediction class')
        if row['observed_t20'] is None:
            unobserved[label] += 1
        else:
            output[label][row['observed_t20']] += 1
    return dict(observed=output,unobserved=dict(unobserved))


def root_family(fatal):
    root = fatal.get('root') or {}
    events = [root.get('event') or {}, *root.get('chain',[]), *root.get('frames',[])]
    text = '\n'.join(event.get('message', event.get('text','')) for event in events)
    if fatal.get('status') != 'termination-found' or root.get('status') == 'unknown':
        return 'unknown'
    if 'setSupportActionBar' in text or 'already has an action bar' in text.lower() or 'Window.FEATURE_SUPPORT_ACTION_BAR' in text:
        return 'appcompat-actionbar-theme'
    if 'WebViewFactory.getProvider' in text:
        return 'webview-provider'
    if 'WebSettings' in text or ('getSettings' in text and ('NullPointerException' in text or 'must not be null' in text)):
        return 'webview-settings-null'
    if 'com.getcapacitor' in text and 'null' in text:
        return 'capacitor-bridge-null'
    return 'other-termination-root'


def runtime_facts(folder, state):
    for parent in [folder,*list(folder.parents)[:5]]:
        path = parent/'facts.txt'
        if not path.is_file():
            continue
        text = path.read_text(errors='replace')
        matches = {field:re.search(field+r' fingerprint=([0-9a-f]{12,64})',text) for field in state}
        if not all(matches.values()):
            continue
        if any(matches[field][1][:12] != pin[:12] for field,pin in state.items()):
            raise ValueError('Run facts runtime/image mismatch')
        return dict(sha256=digest(path.read_bytes()), scope='Matching short runtime/image fingerprints, not fresh per-file byte attestation')
    return None


def diagnostics(roots, frozen, state):
    output = {}
    for run_root in roots:
        if not run_root.is_dir():
            raise ValueError('Missing raw run root')
        for path in sorted(run_root.rglob('record.json')):
            record = json.loads(path.read_text())
            key = record.get('key')
            if key not in frozen['actionbar']:
                continue
            if key in output:
                raise ValueError('Duplicate raw run attempt: '+key+'; select only signed attempts')
            expected = frozen['actionbar'][key]
            if any(record.get(field) != expected[field] for field in ['package','apk_sha256']):
                raise ValueError('Run APK/package mismatch: '+key)
            facts = runtime_facts(path.parent,state)
            entry = dict(record_sha256=digest(path.read_bytes()), run_relative=str(path.parent.relative_to(run_root)),
                facts=facts, apk_identity='record-matches-frozen-SHA; not a fresh installed-byte readback',
                checkpoint='unknown-no-positive-API-crossing-witness')
            if facts is None:
                entry.update(status='unbound-run-state', family='unknown')
            elif not (path.parent/'hilog.txt').is_file():
                entry.update(status='missing-hilog', family='unknown')
            else:
                _,events,pids,reports,disappeared,binding = first_fatal.load_run(path.parent)
                fatal = first_fatal.analyze(events,pids,reports,disappeared)
                entry.update(status=fatal['status'],family=root_family(fatal),first_fatal=fatal,binding=binding)
            output[key] = entry
    return output


def build(frozen, prior, signed, replay=False, logs=None):
    observed = signoff(signed, frozen['cv2'] if replay else frozen['actionbar'], BASELINE_STATE if replay else U8_STATE)
    logs = logs or {}
    cv2_rows = []
    for key,prediction in frozen['cv2'].items():
        actual = observed.get(key)
        verdict = actual['verdict'] if actual else None
        positive = prediction['t20']=='own-ui'
        cv2_rows.append(dict(key=key,predicted_t20=prediction['t20'],observed_t20=verdict,
            functional_score='unobserved' if verdict is None else 'abstention' if not positive else 'hit' if verdict=='lit' else 'overprediction',
            own_ui_score='unobserved' if verdict is None else 'abstention' if not positive else 'hit' if verdict in OWN_UI else 'overprediction',
            first_wall_score='abstention-unknown-prediction',checkpoint_score='abstention-unknown-prediction'))
    cv2_matrix = matrix(['own-ui','unknown'],cv2_rows,'predicted_t20')
    positive_count = sum(cv2_matrix['observed']['own-ui'].values())
    cv2 = dict(rows=cv2_rows,confusion=cv2_matrix,
        metrics=dict(observed_positive_predictions=positive_count,
            functional_precision=dict(numerator=cv2_matrix['observed']['own-ui']['lit'],denominator=positive_count),
            own_ui_precision=dict(numerator=sum(cv2_matrix['observed']['own-ui'][value] for value in OWN_UI),denominator=positive_count),
            abstentions=sum(cv2_matrix['observed']['unknown'].values()),true_negative=None,false_negative=None,binary_accuracy=None),
        late_freeze=True, timing='Original cv2 v1 late freeze retained; not converted into a new pre-U8 forecast')
    change_table = changes(frozen,prior,observed)
    by_change = {row['key']:row for row in change_table['rows']}
    actionbar_rows = []
    for key,prediction in frozen['actionbar'].items():
        actual = observed.get(key)
        evidence = logs.get(key,{})
        candidate = prediction['actionbar_schedule'] in {'startup-or-calibrated-first-content','later-activity-only'}
        actionbar_rows.append(dict(key=key,tier=prediction['actionbar_schedule'],observed_t20=actual['verdict'] if actual else None,
            baseline_visual=prior[key]['visual'],own_ui_change=by_change[key]['own_ui_change'],
            observed_first_fatal_family=evidence.get('family','unknown'),
            wall_score='termination-linked-ActionBar-observed' if candidate and evidence.get('family')=='appcompat-actionbar-theme' else 'unknown-exposure-or-other-first-wall',
            page_exercised='unknown-no-positive-page-exercise-receipt',checkpoint_score=evidence.get('checkpoint','unknown-no-positive-API-crossing-witness'),
            limits='Risk tier is not predicted death; lit t20 cannot disprove a later-only candidate; a different first wall does not prove this call passed'))
    tiers = {}
    for tier in ['startup-or-calibrated-first-content','later-activity-only']:
        selected = [row for row in actionbar_rows if row['tier']==tier]
        tiers[tier] = dict(keys=len(selected), observed_t20=dict(Counter(row['observed_t20'] or 'unobserved' for row in selected)),
            own_ui_changes=dict(Counter(row['own_ui_change'] for row in selected)),
            wall_scores=dict(Counter(row['wall_score'] for row in selected)), binary_accuracy=None)
    controls = [row for row in actionbar_rows if row['tier']=='later-activity-only' and prior[row['key']]['own_ui']]
    actionbar = dict(rows=actionbar_rows,tiers=tiers,previously_lit_later_only=dict(keys=len(controls),
        keys_list=[row['key'] for row in controls],changes=dict(Counter(row['own_ui_change'] for row in controls))),
        timing='Retrospective U7 risk map; no invented t20 forecast or binary miss rate')
    webview_rows = []
    for key,prediction in frozen['webview'].items():
        actual = observed.get(key)
        verdict = actual['verdict'] if actual else None
        evidence = logs.get(key,{})
        predicted_family = 'webview-settings-null' if prediction['first_screen_prediction']=='blocked-WebSettings-null' else 'capacitor-bridge-null' if 'Capacitor-bridge-null' in prediction['first_screen_prediction'] else None
        observed_family = evidence.get('family','unknown')
        wall_score = 'unknown-no-terminal-family-or-nonterminal-forecast'
        if predicted_family and observed_family != 'unknown':
            wall_score = 'family-hit-needs-callsite-review' if predicted_family == observed_family else 'family-mismatch-no-checkpoint-inference'
        webview_rows.append(dict(key=key,predicted_t20=prediction['predicted_t20'],observed_t20=verdict,
            t20_score='unobserved' if verdict is None else 'hit' if verdict==prediction['predicted_t20'] else 'mismatch',
            predicted_first_screen=prediction['first_screen_prediction'],predicted_next_wall=prediction['next_wall_candidate'],
            predicted_first_fatal_family=predicted_family,observed_first_fatal_family=observed_family,
            first_wall_score=wall_score,provider_checkpoint_score='unknown-no-positive-provider-execution-witness',
            confidence=prediction['confidence'],criterion=prediction['criterion']))
    webview = dict(rows=webview_rows,confusion=matrix(VERDICTS,webview_rows,'predicted_t20'),
        exact_t20=dict(hits=sum(row['t20_score']=='hit' for row in webview_rows),observed=sum(row['observed_t20'] is not None for row in webview_rows)),
        late_freeze=True,timing='WebView frozen 11:34:35 after rollout LOCK 11:29:25; no U8 target observations used then')
    return dict(schema='u8-three-freeze-scoring-v1',mode='cv2-structure-replay-not-U8' if replay else 'formal-U8-key-signed-visual',
        formal=not replay,observed_keys=len(observed),expected_keys=166,cv2=cv2,actionbar=actionbar,webview=webview,changes=change_table,
        diagnostics=logs,observed_counts=dict(Counter(row['verdict'] for row in observed.values())),
        provenance=dict(signed_by=signed['signed_by'],board_entry=signed['board_entry'],state=signed['state'],
            frozen_csv_sha256={name:pin for name,(_,pin,_) in PINS.items()},
            visual_scope='Outer key-signed t20; signoff schema does not attest installed APK bytes. Optional matching records/facts and PID logs are a separate evidence axis.',
            scorer_sha256=digest(Path(__file__).read_bytes())),
        limits=['No screenshot-based exception or checkpoint inference', 'Unknown is abstention, not negative',
            'Raw root classifier reports families; call/page exposure and complete causal attribution still require review',
            'Replay omits 66 old keys rather than fabricating outcomes; never use replay artifacts as a formal U8 score'])


def table_text(rows, fields):
    stream = io.StringIO()
    writer = csv.DictWriter(stream,fields,lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({field:row.get(field) for field in fields})
    return stream.getvalue()


def markdown(result):
    lines = ['# Three-freeze scoring', '', 'Mode: **'+result['mode']+'**; observed '+str(result['observed_keys'])+'/166 keys.',
             '', 'cv2 unknown is abstention; ActionBar tiers are risks, not a t20 binary prediction. WebView fallback is not functional lit.',
             '', '## cv2 confusion', '', '| Prediction | '+' | '.join(VERDICTS)+' |', '|---|'+'---|'*len(VERDICTS)]
    for label,values in result['cv2']['confusion']['observed'].items():
        lines.append('| '+label+' | '+' | '.join(str(values[verdict]) for verdict in VERDICTS)+' |')
    lines += ['', '## ActionBar tiers', '', '| Tier | Keys | Observed visual classes |', '|---|---:|---|']
    for tier,values in result['actionbar']['tiers'].items():
        lines.append('| '+tier+' | '+str(values['keys'])+' | '+json.dumps(values['observed_t20'],sort_keys=True)+' |')
    lines += ['', 'WebView exact t20: '+str(result['webview']['exact_t20']['hits'])+'/'+str(result['webview']['exact_t20']['observed'])+'.',
              '', 'U7→current app-owned-UI changes: '+json.dumps(result['changes']['own_ui_counts'],sort_keys=True)+'.',
              '', 'All historical late/retrospective labels remain. First wall and checkpoints are not supplied by visual signoff.',
              'Optional diagnostic roots are terminal-first/PID-bound and must match runtime/image facts; duplicate attempts are refused.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--signoff',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay-cv2',action='store_true')
    parser.add_argument('--run-root',type=Path,action='append',default=[])
    args = parser.parse_args(argv)
    try:
        frozen = predictions()
        prior,baseline_pins = baselines(frozen)
        payload = args.signoff.read_bytes()
        signed = json.loads(payload)
        signoff(signed,frozen['cv2'] if args.replay_cv2 else frozen['actionbar'],BASELINE_STATE if args.replay_cv2 else U8_STATE)
        logs = diagnostics(args.run_root,frozen,BASELINE_STATE if args.replay_cv2 else U8_STATE)
        result = build(frozen,prior,signed,args.replay_cv2,logs)
        result['provenance'].update(signoff_file_sha256=digest(payload),baseline_file_sha256=baseline_pins,
            first_fatal_sha256=digest(Path(first_fatal.__file__).read_bytes()))
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/'SCORING.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        (args.output/'SCORING.md').write_text(markdown(result))
        (args.output/'CHANGES.csv').write_text(table_text(result['changes']['rows'], ['key','package','apk_sha256','baseline_visual','baseline_authority','observed_t20','board','own_ui_change','functional_change','raw_visual_changed']))
        for name in ['cv2','actionbar','webview']:
            fields = list(result[name]['rows'][0])
            (args.output/(name.upper()+'.csv')).write_text(table_text(result[name]['rows'],fields))
        print(json.dumps(dict(mode=result['mode'],observed=result['observed_keys'],changes=result['changes']['own_ui_counts'],webview=result['webview']['exact_t20']),sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
        print('SCORING REFUSED: '+str(error),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
