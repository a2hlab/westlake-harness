#!/usr/bin/env python3
"""Report diagnostics without modifying the frozen forecast or score."""
import csv,datetime,hashlib,json
from pathlib import Path
from collect_results import HERE,verify
def write_csv(path,rows,fields=None):
 fields=fields or list(rows[0])
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) or v is None else v for k,v in r.items()})
def confusion(rows):
 known=[r for r in rows if r['light_eligible']]
 tp=sum(r['expected_lit'] and r['visual']=='lit' for r in known)
 fp=sum(r['expected_lit'] and r['visual']=='not-lit' for r in known)
 fn=sum(not r['expected_lit'] and r['visual']=='lit' for r in known)
 tn=sum(not r['expected_lit'] and r['visual']=='not-lit' for r in known)
 return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'positive_precision':tp/(tp+fp) if tp+fp else None,'positive_recall':tp/(tp+fn) if tp+fn else None,'always_not_lit_baseline':(fp+tn)/len(known) if known else None}
def main():
 freeze=verify();back=json.loads((HERE/'backtest.json').read_text());obs=json.loads((HERE/'observed/observations-reviewed.json').read_text());rows=back['rows']
 allstats=confusion(rows);strictstats=confusion([r for r in rows if r['strict_pre_click']])
 misses=[{**r,'visual_evidence':obs[r['app']]['visual_evidence'],'wall_evidence':obs[r['app']]['first_wall_evidence']} for r in rows if r['light_eligible'] and not r['light_correct']]
 write_csv(HERE/'backtest.csv',rows);write_csv(HERE/'lighting-misses.csv',misses)
 walls=[r for r in rows if r['wall_observed'] and not r['wall_correct']];write_csv(HERE/'wall-misses.csv',walls,list(rows[0]))
 result={'task':'r16-prospective','phase':'evaluated','frozen_at':freeze['frozen_at'],'predictions_sha256':hashlib.sha256((HERE/'predictions.json').read_bytes()).hexdigest(),'expected_lit':16,'observed_lit':9,'keys':66,'captured':sum(r['captured'] for r in obs.values()),'alive_t5':sum(bool(r['target_uid_processes']['t5']) for r in obs.values()),'t20':'unknown; not sampled','strict_pre_click_keys':sum(r['strict_pre_click'] for r in rows),'lighting':back['all_exact_adjudicated']['lighting'],'strict_pre_click_lighting':back['strict_pre_click']['lighting'],'confusion':allstats,'strict_pre_click_confusion':strictstats,'first_wall':back['all_exact_adjudicated']['first_wall_classified_forecasts'],'first_wall_including_abstentions':back['all_exact_adjudicated']['first_wall_including_forecast_abstentions'],'strict_first_wall_including_abstentions':back['strict_pre_click']['first_wall_including_forecast_abstentions'],'first_wall_observation_unknowns':[k for k,r in obs.items() if r['visual']=='not-lit' and r['first_wall']=='unknown'],'excluded':['subwaysurfers: executor rejected actual APK SHA; no screenshot or click'],'profile_note':'Both run baselines pin r16 JAR and d977 host. Native A/B differences remain; overall misses retain these cases. HAP grant/socket success is not inferred from deployment.','r2':{'forecast_integrity':'verified','screenshot_outcomes':'outer-adjudicated, screenshot hashes verified','scoring':'verified under frozen rules','first_wall_root_cause':'partially: target-PID exception-chain interpretation; repair causality unverified','network_content':'Noice keys remain network-error UI per outer; own-UI success does not prove networking fixed'},'updated_at':datetime.datetime.now().astimezone().isoformat()}
 (HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
