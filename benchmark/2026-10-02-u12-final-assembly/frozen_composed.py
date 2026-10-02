"""Offline frozen artifact checks over each complete predicted process-view identity."""
import argparse,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'));import check_frozen as f
p=argparse.ArgumentParser();p.add_argument('--surface',choices=['mac','vm'],required=True);a=p.parse_args()
c=json.loads((H/'composition.json').read_text());entries=f.active(f.load(R/'knowledge/frozen/frozen.json'));rows={}
for serial,row in c['candidate_boards'].items():
 lines,bad=f.check_artifacts(entries,row['expected'],'U12 final '+serial[:8]);rows[serial]={'lines':lines,'violations':bad}
out=H/'gates'/a.surface;(out/'frozen-composed.json').write_text(json.dumps(rows,indent=2)+'\n')
summary=out/'summary.json';data=json.loads(summary.read_text());data['frozen_composed_violations']=sum(r['violations'] for r in rows.values());summary.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({s:r['violations'] for s,r in rows.items()},indent=2))
raise SystemExit(0 if not data['frozen_composed_violations'] else 2)
