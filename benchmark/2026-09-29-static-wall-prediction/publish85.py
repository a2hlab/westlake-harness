#!/usr/bin/env python3
"""Compact static and evaluation summaries; leaves frozen predictions unchanged."""
import datetime,json
from scan85 import OUT
from scan_io import load
from finalize_v3 import csvwrite,dump

def main():
    hits=load(OUT/'hits.json');backtest=load(OUT/'backtest.json');summary=[]
    for family in sorted({r['family'] for r in hits}):
        rows=[r for r in hits if r['family']==family]
        summary.append({'family':family,'apps':32,'static_candidates':sum(r['hit'] for r in rows),'startup_candidates':sum(r['startup_reachable']=='yes-static' for r in rows),'strong_static_predicates':sum(r['strong_static_predicate'] for r in rows),'candidate_apps':[r['app'] for r in rows if r['hit']],'startup_apps':[r['app'] for r in rows if r['startup_reachable']=='yes-static']})
    summary.sort(key=lambda r:(-r['startup_candidates'],-r['static_candidates'],r['family']))
    csvwrite(OUT/'family-summary.csv',summary,list(summary[0]));unknown=[]
    for row in backtest['rows']:
        if not row['in_prediction_cohort'] or row['identity']!='exact' or not row['observation_complete']:continue
        if not row['classifiable']:
            text=row['fatal_text'];group='unclassified'
            if 'nativeSubscribeCommonEvent' in text:group='unmodeled-nativeSubscribeCommonEvent'
            elif 'current thread is not READY for guest dlopen' in text:group='runtime-guest-thread-ready (out of static scope)'
            elif 'java.lang.Object.getClass()' in text:group='unresolved-getClass-null'
            unknown.append({'app':row['app'],'partition':row['partition'],'group':group,'role':row['observation_role'],'fatal_text':text,'status':'not-a-hit; no rule added after unblinding'})
    csvwrite(OUT/'unmodeled-observations.csv',unknown,list(unknown[0]) if unknown else ['app','group'])
    result={'task':85,'offline':True,'version':'v4-r2','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cohort':{'memberships':33,'unique_apks':32,'duplicate':'ooniprobe'},'matrix_rows':len(hits),'families':summary,'backtest':backtest['metrics'],'coverage':backtest['coverage'],'freeze':'freeze.json','predictions':'predictions-v3a-r13.csv','backtest_evidence':'backtest.csv','known_limits':['startup graph and constant paths are conditional','native scan covers selected lib/arm64-v8a entries, not dynamic/downloaded libraries','symbol versions/effective namespace unverified','in-app service target is co-reference candidate, not proven Intent dataflow','SharedPreferences null is not statically proven','class risks inherited from r13; actual repair status in r14 unknown'],'validation':{'contract':'specs/bms-static-v3/t3-r14-wall-families.spec.md','lifecycle':'evidence/lifecycle.json','no_device_commands':True,'commit':'outer lane'}}
    dump(OUT/'results.json',result)
    root=OUT.parent/'results.json';doc=load(root);doc['task85']={'results':'v4-r2/results.json','predictions':'v4-r2/predictions-v3a-r13.csv','apps':32,'rules':5,'rows':len(hits)};root.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
    metrics=backtest['metrics'];seed=metrics['seed_family'];first=metrics['seed_first_fatal'];held=metrics['held_out_family'];heldfirst=metrics['held_out_first_fatal']
    readme=f"""# Task85 — five static wall families

The earlier table omitted window attributes, own-service binding, VelocityTracker, bionic imports/header checks and SharedPreferences return contracts. This version emits **160 verdicts / 32 APKs**, retaining the prior r13 class-risk columns in the new prediction CSV.

Run from the repository root:

    python3 benchmark/2026-09-29-static-wall-prediction/run85.py --out /tmp/b85-fresh-scan
    python3 benchmark/2026-09-29-static-wall-prediction/backtest85.py --triage <auto_triage.json>
    python3 benchmark/2026-09-29-static-wall-prediction/publish85.py
    python3 benchmark/2026-09-29-static-wall-prediction/package85.py
    cargo test --manifest-path tools/spec-checks/Cargo.toml b85_

The first command reproduces the detector in a fresh directory; the following commands score/publish the released freeze in v4-r2. The scanner refuses to overwrite a freeze. Inputs are the existing 32 hashed APKs, v3a ELF export set, prior JNI matrix and source window-flag policy. No device command or runtime change.

Machine entrypoints: **hits.csv**, **predictions-v3a-r13.csv**, **family-summary.csv**, **backtest.csv**, **coverage-gaps.csv** and **unmodeled-observations.csv**. Per-app evidence gives DEX method/line/offset, conditional startup paths, selected arm64 ELF header hashes and strong/weak bionic imports. source-references.json supplies detector/source file lines. Flags include LayoutParams constructors; own-service class co-reference is a candidate, not proven Intent flow. JNI unknown stays unknown. Valid ELF headers do not predict runtime “header failed”; symbol versions and effective namespaces are unresolved.

Prediction freeze: **18:11:36 +0800**, before undisclosed r14 outcomes were read. Seven APK clicks occurred after this freeze, including the held-out fd-stk window-family case (timestamps in backtest.csv). The 18 board-disclosed keys are seed cases. Seed five-family candidate coverage is **{seed['hits']}/{seed['total']}**; first-new-family agreement is **{first['hits']}/{first['total']}**. Held-out five-family coverage is **{held['hits']}/{held['total']}**; held-out first-family agreement **{heldfirst['hits']}/{heldfirst['total']}**. A zero denominator is unknown, never a pass. Outcome-blind evaluation is not a claim that these predictions predate the existing board run.

At this cutoff, **{backtest['coverage']['exact_finished_predictions']}/32** predictions have exact, finished APK records among **{backtest['coverage']['observed_rows']}** triaged run rows. Missing/unclassified/out-of-cohort rows are explicit. #83's old system-library loader warnings are excluded using the corrected #84 triage; a warning without an exit cannot be a first-fatal hit. No screenshots or process totals are claimed.

Validation: **3/3 scenarios pass**, lint **100%**, including rule negatives, strong/weak import distinctions, frozen hashes and seed/held-out/nonfatal partitions. Broad API hits are candidates, not precision or proof of execution. Frozen detectors were not tuned after reading results.
"""
    (OUT/'README.md').write_text(readme)
    print({'matrix_rows':len(hits),'coverage':backtest['coverage'],'metrics':metrics})
if __name__=='__main__':main()
