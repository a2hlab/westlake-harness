#!/usr/bin/env python3
"""Summarize existing local raw receipts only."""
from pathlib import Path
import hashlib,json
from policy import maps_snapshot,check_coverage,need
HERE=Path(__file__).resolve().parent
BASE=Path.home()/'.local/share/westlake/commercial-game-20261021/apk-extractor'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    raw=BASE/'fresh-next-01';records=json.loads((raw/'records.json').read_text());need(len(records)==8,'8commands')
    for r in records:
        need(r['transport_rc']==0 and str(r['remote_rc'])=='0','rc')
        for suffix in ['stdout','stderr']:need(sha(raw/(r['id']+'.'+suffix))==r[suffix+'_sha256'],'raw digest')
    snapshot=maps_snapshot((raw/'all-process-maps.stdout').read_text());check_coverage(snapshot,(raw/'processes-before.stdout').read_text(),(raw/'processes-after.stdout').read_text())
    profile=json.loads((raw/'installs-profile.stdout').read_text().split('__REMOTE_RC')[0])
    report=dict(raw_alias='$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/fresh-next-01',commands=8,all_rc_zero=True,processes=snapshot['count'],stable_birth_parent=True,consumers=snapshot['hits'],coverage='all persistent ps entries covered; only own hdcd sh/ps outside scan',maps_bytes=(raw/'all-process-maps.stdout').stat().st_size,maps_sha256=sha(raw/'all-process-maps.stdout'),init_cfg_sha256='ce66b98079b4334a0b1d534e794ea484d8b8b64831e5d9db0abd9a783a466a8e',ondemand=True,profile=profile,profile_stdout_sha256=sha(raw/'installs-profile.stdout'),profile_file_sha256=None,decision='no preliminary foundation stop; repeat under lock')
    (HERE.parent/'window-prep/fresh-next-review.json').write_text(json.dumps(report,indent=2)+'\n')
    raw=BASE/'runtime-fresh-01';records=json.loads((raw/'records.json').read_text());need(len(records)==11 and all(r['transport_rc']==0 and str(r['remote_rc'])=='0' for r in records),'runtime11rc')
    comparison=json.loads((raw/'comparison.json').read_text());need(all(not x['diff'] for x in comparison.values()),'runtime changed')
    report=dict(raw_alias='$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/runtime-fresh-01',comparison=comparison,commands=11,all_rc_zero=True,ready_stdout=(raw/'ready.stdout').read_text().strip(),boot_before=(raw/'boot-before.stdout').read_text().splitlines()[0],boot_after=(raw/'boot-after.stdout').read_text().splitlines()[0],raw=[dict(file=f.name,sha256=sha(f)) for f in sorted(raw.iterdir()) if f.is_file()],decision='reuse160 exact members; appspawn-x declared ondemand; do not infer runtime broken from missing PID')
    need(report['boot_before']==report['boot_after']=='a1d869b4-69a2-40a4-937e-4860f5b54239','boot bracket')
    (HERE/'runtime-review.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
