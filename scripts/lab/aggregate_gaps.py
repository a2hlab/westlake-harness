"""Merge per-app gap maps into one leaderboard: which open gaps block the most apps.

usage: aggregate_gaps.py <static dir> <corpus.json>
Writes <static dir>/LEADERBOARD.md and leaderboard.json. Counts are static (APK + provider source); once board
runs exist, weight them by the first observed blocker per app instead (process spec section 13).
"""
import collections, json, sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: aggregate_gaps.py <static dir> <corpus.json>")
d = Path(sys.argv[1]); corpus = json.loads(Path(sys.argv[2]).read_text())["apps"]
HARD = {"missing", "null", "strict", "denied", "stub", "hollow", "unresolved", "absent"}
rows_by_id, members = collections.defaultdict(list), collections.defaultdict(set)
available = {p.name for p in (d / "maps").iterdir() if (p / "gap-map.json").exists()}
ignored_apps = sorted(available - set(corpus))
missing_apps = sorted(set(corpus) - available)
if missing_apps:
    raise SystemExit("missing corpus maps: " + ", ".join(missing_apps))
apps = sorted(corpus)
for app in apps:
    for r in json.loads((d / "maps" / app / "gap-map.json").read_text())["rows"]:
        if r.get("verdict") in ("supplied", None): continue
        rows_by_id[r["id"]].append((app, r))
        if r.get("category") == "java-api":
            for m in r.get("members") or []:
                if m.get("kind") in ("absent_class", "absent_method", "absent_field", "missing_member", "absent"):
                    members[f"{m.get('owner')}->{m.get('name')}"].add(app)
board = []
for gid, hits in rows_by_id.items():
    verdicts = collections.Counter(r["verdict"] for _, r in hits)
    first = hits[0][1]
    board.append({"id": gid, "apps": len({a for a, _ in hits}), "verdicts": dict(verdicts), "hard": any(v in HARD for v in verdicts),
                  "class": first.get("shim_class"), "effort": first.get("effort"), "oh": first.get("oh_touchpoint"),
                  "shim": first.get("shim"), "which": sorted({a for a, _ in hits})})
board.sort(key=lambda b: (-b["apps"], not b["hard"], b["id"]))
stacks = collections.Counter(corpus.get(a, {}).get("stack", "?").split(" ")[0] for a in apps)
(d / "leaderboard.json").write_text(json.dumps({"apps": apps, "ignored_apps": ignored_apps, "gaps": board, "top_missing_members": sorted(((len(v), k) for k, v in members.items()), reverse=True)[:40]}, indent=1) + "\n")
lines = [f"# Open-gap leaderboard — {len(apps)} apps (static)", "", "Stacks: " + ", ".join(f"{k} {v}" for k, v in stacks.most_common()), "",
         "| # apps | gap | verdicts | class | effort | OH touchpoint | shim |", "|---:|---|---|---|---|---|---|"]
for b in board[:60]:
    lines.append(f"| {b['apps']} | {'**' if b['hard'] else ''}{b['id']}{'**' if b['hard'] else ''} | {', '.join(f'{k}×{v}' for k, v in b['verdicts'].items())} | {b['class']} | {b['effort']} | {b['oh'] or ''} | {(b['shim'] or '')[:70]} |")
lines += ["", "## Ignored maps outside corpus", "", ", ".join(f"`{a}`" for a in ignored_apps) or "None."]
lines += ["", "Bold: at least one app has a hard verdict (missing, null, strict, denied, stub, hollow, unresolved).", "",
          "## Most widely referenced absent Java members", "", "| # apps | member |", "|---:|---|"]
for n, k in sorted(((len(v), k) for k, v in members.items()), reverse=True)[:25]:
    lines.append(f"| {n} | `{k}` |")
(d / "LEADERBOARD.md").write_text("\n".join(lines) + "\n")
print(f"{len(apps)} apps, {len(board)} distinct open gaps, {sum(b['hard'] for b in board)} with a hard verdict -> {d/'LEADERBOARD.md'}")
