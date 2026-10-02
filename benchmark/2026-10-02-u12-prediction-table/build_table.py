#!/usr/bin/env python3
"""Build U12 prediction table: join 7 master sources on the 51 non-lit keys from candidate-first-fatal-clusters.

Inputs (all master, read-only):
- benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json (51 keys, cluster signatures)
- benchmark/2026-10-02-u12-java-walls/predictions.csv (13 keys, u12r2_fix, predicted_first_fatal_moves)
- benchmark/2026-10-02-u12-mediandk/predictions.json (1 key, current_first_fatal)
- benchmark/2026-10-02-u12-icu-zeroinit/results.json (2 keys, prediction)
- benchmark/2026-10-02-u12-disappeared/predictions.json (6 keys, cluster)
- benchmark/2026-10-02-u12-sigabrt/results.json (8 keys, cluster, proposed_fix)
- benchmark/2026-10-02-n11h-predictions/n11h-predictions.csv (18 keys, prediction, confidence)

Output: u12-predictions.csv (one row per key, 51 rows), README.md, landing-paths.txt.
"""
import csv, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Load sources
clusters = json.loads((REPO / 'benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json').read_text())
java_walls = list(csv.DictReader((REPO / 'benchmark/2026-10-02-u12-java-walls/predictions.csv').open()))
mediandk = json.loads((REPO / 'benchmark/2026-10-02-u12-mediandk/predictions.json').read_text())
icu = json.loads((REPO / 'benchmark/2026-10-02-u12-icu-zeroinit/results.json').read_text())
disappeared = json.loads((REPO / 'benchmark/2026-10-02-u12-disappeared/predictions.json').read_text())
sigabrt = json.loads((REPO / 'benchmark/2026-10-02-u12-sigabrt/results.json').read_text())
n11h = list(csv.DictReader((REPO / 'benchmark/2026-10-02-n11h-predictions/n11h-predictions.csv').open()))

# Build key -> cluster map from clusters.json
key_cluster = {}
for c in clusters:
    for k in c['keys']:
        key_cluster[k] = {'kind': c['signature']['kind'], 'cause': c['signature']['cause']}

# 51 non-lit keys
keys = sorted(key_cluster.keys())

# Build per-key rows
rows = []
for key in keys:
    row = {'key': key, 'cluster_kind': key_cluster[key]['kind'], 'cluster_cause': key_cluster[key]['cause']}
    # java_fix / java_moves
    jw = next((r for r in java_walls if r['key'] == key), None)
    row['java_fix'] = jw['u12r2_fix'] if jw else ''
    row['java_moves'] = jw['predicted_first_fatal_moves'] if jw else ''
    # mediandk
    md = next((r for r in mediandk['rows'] if r['key'] == key), None)
    row['mediandk'] = md['current_first_fatal'] if md else ''
    row['mediandk_moves'] = str(md.get('conditional_first_wall_moved', '')) if md else ''
    # icu
    row['icu'] = icu['prediction'].get(key, {}).get('after', '') if key in icu.get('keys', []) else ''
    # disappeared
    dis = next((r for r in disappeared if r['key'] == key), None)
    row['disappeared'] = dis['cluster'] if dis else ''
    # sigabrt
    sig = next((r for r in sigabrt['clusters'] if key in r['keys']), None)
    row['sigabrt'] = (sig['id'] + ' | ' + sig.get('observable_root', sig.get('proposed_fix', ''))[:80]) if sig else ''
    # n11h
    nh = next((r for r in n11h if r['key'] == key), None)
    row['n11h_family'] = nh['prediction'] + ' | ' + nh['confidence'] if nh else ''
    # owners / any_predicted_mover
    fix_cols = ['java_fix', 'mediandk', 'icu', 'disappeared', 'sigabrt']
    row['owners'] = sum(1 for c in fix_cols if row[c])
    row['any_predicted_mover'] = 'yes' if row['java_moves'] == 'yes' or any(row[c] for c in ['icu', 'disappeared', 'sigabrt']) or (row['mediandk_moves'] == 'True') else 'no'
    rows.append(row)

# Write CSV
out = REPO / 'benchmark/2026-10-02-u12-prediction-table'
out.mkdir(parents=True, exist_ok=True)
with open(out / 'u12-predictions.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['key', 'cluster_kind', 'cluster_cause', 'java_fix', 'java_moves', 'mediandk', 'mediandk_moves', 'icu', 'disappeared', 'sigabrt', 'n11h_family', 'owners', 'any_predicted_mover'])
    w.writeheader()
    w.writerows(rows)

# Write README
with open(out / 'README.md', 'w') as f:
    f.write('# U12 prediction table\n\n')
    f.write('## Inputs (master, read-only)\n\n')
    for src in ['benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json', 'benchmark/2026-10-02-u12-java-walls/predictions.csv', 'benchmark/2026-10-02-u12-mediandk/predictions.json', 'benchmark/2026-10-02-u12-icu-zeroinit/results.json', 'benchmark/2026-10-02-u12-disappeared/predictions.json', 'benchmark/2026-10-02-u12-sigabrt/results.json', 'benchmark/2026-10-02-n11h-predictions/n11h-predictions.csv']:
        f.write(f'- `{src}`\n')
    f.write('\n## Counts\n\n')
    f.write(f'- rows: {len(rows)}\n')
    f.write(f'- java_fix: {sum(1 for r in rows if r["java_fix"])}/{len(java_walls)}\n')
    f.write(f'- java_moves: {sum(1 for r in rows if r["java_moves"])}/{len(java_walls)}\n')
    f.write(f'- mediandk: {sum(1 for r in rows if r["mediandk"])}/{len(mediandk["rows"])}\n')
    f.write(f'- icu: {sum(1 for r in rows if r["icu"])}/{len(icu["keys"])}\n')
    f.write(f'- disappeared: {sum(1 for r in rows if r["disappeared"])}/{len(disappeared)}\n')
    f.write(f'- sigabrt: {sum(1 for r in rows if r["sigabrt"])}/{sum(len(c["keys"]) for c in sigabrt["clusters"])}\n')
    f.write(f'- n11h: {sum(1 for r in rows if r["n11h_family"])}/{len(n11h)}\n')
    f.write(f'- owners >= 2: {sum(1 for r in rows if r["owners"] >= 2)}\n')
    f.write(f'- any_predicted_mover: {sum(1 for r in rows if r["any_predicted_mover"] == "yes")}\n')
    f.write('\n## Owners >= 2 (conflict keys)\n\n')
    for r in rows:
        if r['owners'] >= 2:
            f.write(f'- `{r["key"]}`: owners={r["owners"]}, java_fix={r["java_fix"][:60]}, mediandk={r["mediandk"][:60]}, icu={r["icu"][:60]}, disappeared={r["disappeared"][:60]}, sigabrt={r["sigabrt"][:60]}, n11h={r["n11h_family"][:60]}\n')

# Write landing-paths
with open(out / 'landing-paths.txt', 'w') as f:
    f.write('benchmark/2026-10-02-u12-prediction-table/u12-predictions.csv\n')
    f.write('benchmark/2026-10-02-u12-prediction-table/README.md\n')
    f.write('benchmark/2026-10-02-u12-prediction-table/landing-paths.txt\n')

print(f'rows {len(rows)}')
print(f'java_walls not-in-51: {[r["key"] for r in java_walls if r["key"] not in keys] or "none"}')
print(f'mediandk not-in-51: {[r["key"] for r in mediandk["rows"] if r["key"] not in keys] or "none"}')
print(f'icu not-in-51: {[k for k in icu.get("keys", []) if k not in keys] or "none"}')
print(f'disappeared not-in-51: {[r["key"] for r in disappeared if r["key"] not in keys] or "none"}')
print(f'sigabrt not-in-51: {[k for c in sigabrt["clusters"] for k in c["keys"] if k not in keys] or "none"}')
print(f'n11h not-in-51: {[r["key"] for r in n11h if r["key"] not in keys] or "none"}')
print(f'java_fix {sum(1 for r in rows if r["java_fix"])}/{len(java_walls)}')
print(f'mediandk {sum(1 for r in rows if r["mediandk"])}/{len(mediandk["rows"])}')
print(f'icu {sum(1 for r in rows if r["icu"])}/{len(icu["keys"])}')
print(f'disappeared {sum(1 for r in rows if r["disappeared"])}/{len(disappeared)}')
print(f'sigabrt {sum(1 for r in rows if r["sigabrt"])}/{sum(len(c["keys"]) for c in sigabrt["clusters"])}')
print(f'n11h {sum(1 for r in rows if r["n11h_family"])}/{len(n11h)}')
print(f'owners >= 2: {[r["key"] for r in rows if r["owners"] >= 2]}')
print(f'any_predicted_mover: {[r["key"] for r in rows if r["any_predicted_mover"] == "yes"]}')
