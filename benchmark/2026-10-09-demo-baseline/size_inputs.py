#!/usr/bin/env python3
"""Read APK sizes for the full signed gallery superset; no device access."""
import json
import os
from pathlib import Path
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
r=Path(__file__).resolve().parents[2];ws=Path(os.environ.get('WORKSPACES',str(r.parent)))
src=r/'benchmark/2026-10-08-lit-apps-report/apps.json';d=json.loads(src.read_text());rows=[];seen=set()
for x in d['apps']:
 if x['package'] in seen: continue
 seen.add(x['package']); p=Path(os.path.expandvars(x['apk_path'].replace('$WORKSPACES',str(ws)))).expanduser()
 rows.append({'key':x['key'],'package':x['package'],'apk_path':x['apk_path'],'apk_sha256_from_signed_inventory':x['apk_sha256'],'bytes':p.stat().st_size if p.is_file() else None})
missing=[x['key'] for x in rows if x['bytes'] is None];total=sum(x['bytes'] or 0 for x in rows)
result={'source':'benchmark/2026-10-08-lit-apps-report/apps.json','distinct_packages':len(rows),'missing':missing,'apk_bytes':total,'apk_times_3_bytes':total*3,'scope':'128-package signed gallery superset; final demo manifest pending; excludes pending Toutiao/BoatAttack extras','board_access':False,'rows':rows}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
raise SystemExit(2 if missing else 0)
