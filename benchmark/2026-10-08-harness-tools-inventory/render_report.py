#!/usr/bin/env python3
"""Render the evidence catalogue and a dependency-free SVG chart; never run lab tools."""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_URL = 'https://github.com/A2OH/westlake-harness'


def link(path, snapshot, line=None):
    return f'{REPO_URL}/blob/{snapshot}/{path}' + (f'#L{line}' if line else '')


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def main():
    data = json.loads((HERE/'tools.json').read_text())
    snap = data['snapshot_commit']
    rows = data['tools']
    summary = data['summary']
    operational = [r for r in rows if r['category'] != 'testing']
    days = collections.defaultdict(collections.Counter)
    for r in rows:
        days[r['first_commit']['date']]['tests' if r['category']=='testing' else 'operational'] += 1
    running = {'tests': 0, 'operational': 0}
    daily = []
    for day, counts in sorted(days.items()):
        for kind in running:
            running[kind] += counts[kind]
        daily.append({'date': day, 'added': sum(counts.values()), 'operational_added': counts['operational'],
                      'tests_added': counts['tests'], 'cumulative': sum(running.values()),
                      'operational_cumulative': running['operational'], 'tests_cumulative': running['tests']})
    (HERE/'daily-growth.csv').write_text('date,added,operational_added,tests_added,cumulative\n'+''.join(
        f"{x['date']},{x['added']},{x['operational_added']},{x['tests_added']},{x['cumulative']}\n" for x in daily))
    # A simple factual SVG, generated from the same CSV data. Weekly aggregation
    # has only one non-empty ISO week, so the right panel exposes daily additions.
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430">',
           '<title>Harness source-tool growth at pinned master</title>',
           '<desc>First-add author dates, source files rather than executable command counts; existing tools only.</desc>',
           '<rect width="1000" height="430" fill="#fff"/>',
           '<g font-family="Arial, sans-serif" font-size="13" fill="#243447">',
           '<text x="48" y="28" font-size="19">First recorded in this repository (not original creation date)</text>',
           '<text x="48" y="54">Weekly cumulative files</text><text x="520" y="54">Daily detail: operational tools vs tests/adapters</text>']
    for left in (50,520):
        for yv in (0,100,200,300):
            y = 350-yv*.85
            svg += [f'<line x1="{left}" y1="{y}" x2="{left+420}" y2="{y}" stroke="#dbe2ea"/>',
                    f'<text x="{left-26}" y="{y+4}">{yv}</text>']
    week = data['weekly_growth'][0]
    y = 350-week['cumulative']*.85
    svg += [f'<path d="M75 350 L440 {y}" fill="none" stroke="#2166ac" stroke-width="3"/>',
            f'<circle cx="440" cy="{y}" r="5" fill="#2166ac"/>',
            f'<text x="385" y="{y-12}">{week["cumulative"]} files</text>',
            '<text x="62" y="376">before first addition</text>',
            f'<text x="330" y="376">week {week["week_start"]}</text>']
    for field, color in [('cumulative','#2166ac'),('operational_cumulative','#1b7837'),('tests_cumulative','#b35806')]:
        points = ' '.join(f'{535+i*78},{350-x[field]*.85}' for i,x in enumerate(daily))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
    for i,x in enumerate(daily):
        svg.append(f'<text x="{523+i*78}" y="376">{x["date"][5:]}</text>')
    svg += ['<text x="525" y="402" fill="#2166ac">total</text>',
            '<text x="625" y="402" fill="#1b7837">operational</text>',
            '<text x="760" y="402" fill="#b35806">tests / contract adapters</text>', '</g></svg>']
    (HERE/'growth.svg').write_text('\n'.join(svg)+'\n')
    lang = collections.Counter(r['language'] for r in rows)
    body = [
        '# Harness tools: evidence-bound inventory',
        '',
        'Earlier reports could mistake a file name for a role, a retained reference for an executed call, or a bulk import for the date a tool was created. This inventory separates those claims. It does not run any lab tool or access devices.',
        '',
        f'**Snapshot:** [`{snap[:12]}`]({REPO_URL}/commit/{snap}), committed {data["snapshot_committer_date"]}; inventoried on 2026-10-08. **{summary["total"]} source files = {len(operational)} operational/helper files + {summary["category_counts"]["testing"]} test/replay/contract-adapter files.** The snapshot is five days older than the report date; unlanded work in other worktrees is not silently included.',
        '',
        '## Scope and how tools were generated',
        '',
        f'- `scripts/lab/**`: all **{summary["lab_scripts"]}** tracked `.py` / `.sh` files, including tests and historical ad-hoc patches.',
        '- `scripts/olp-*.sh`, top level only: **0 files**. The `olp-*` harvest/append tools mentioned in operational documents belong to the external octoscode installation; their callers are listed here, their implementation is outside the requested repository scope.',
        f'- `tools/spec-checks/**`: **{summary["rust_files"]} Rust source files** (one library unit and 86 integration-test units). `Cargo.toml`, `Cargo.lock` and `.gitignore` are support files, enumerated in `tools.json`, not counted as executable tools.',
        f'- Actual source languages: {lang["python"]} Python, {lang["shell"]} shell, {lang["rust"]} Rust. `lane_watch.sh` is Python despite its retained `.sh` suffix.',
        '- One file is one catalogue row. Shell/Python wrappers count separately; this is a source-maintenance surface, not the number of independent commands or features. Our generator, validator and new Rust adapter are excluded by the pinned snapshot.',
        '',
        'The recorded generation routes are: (1) version existing lab scripts from westlake-inputs, (2) write small scripts for reconstruction, builds and repeatable probes, (3) turn incidents/user rules into fail-closed checks and executable dispatches, and (4) add Rust `#[test]` adapters that invoke Python evidence checks so agent-spec can select Cargo tests. These are git/header observations, not a claim to know the original human/AI authoring process.',
        '',
        f'In particular, **59 files** first entered together in [`1a2bb87234da`]({REPO_URL}/commit/1a2bb87234da) (“scripts/lab: version the westlake-inputs lab scripts”). Their earlier creation dates are unknown here. History stores both author and committer timestamps; the requested growth counts use the first-add author date. Renames, deleted tools, external tools and untracked files are not counted in this surviving-file cohort.',
        '',
        '## Categories',
        '',
        'The suggested categories are retained, with **environment/transfer/archive** and **tests/contract adapters** split out so build/deploy totals do not hide support or proof code. Each tool has one primary category, chosen from its inspected role. An activation smoke gate may execute board probes, but its primary purpose is admission.',
        '',
        '| Category | Files | Representative role |',
        '|---|---:|---|',
    ]
    from build_inventory import CATEGORIES
    for c,n in summary['category_counts'].items():
        representative = next(x['purpose'] for x in rows if x['category']==c)
        body.append(f'| {CATEGORIES[c]} | {n} | {cell(representative)} |')
    body += [
        '', '## Growth', '',
        'All first-add dates in the requested surviving scope fall in ISO week **2026-W40** (Monday 2026-09-28). There is only one observed weekly growth step; no earlier creation dates or later weeks are invented. The daily inset explains the bulk import and later additions. This is not a historical count of every tool that ever existed.', '',
        '| Week starting | Added | Cumulative |', '|---|---:|---:|',
    ]
    for x in data['weekly_growth']:
        body.append(f'| {x["week_start"]} | {x["added"]} | {x["cumulative"]} |')
    body += ['', '![First-add weekly growth and daily detail](growth.svg)', '',
             '[Weekly data](weekly-growth.csv) · [Daily data](daily-growth.csv)', '',
             '| Date | New operational/helper files | New test/adapter files | Total added |', '|---|---:|---:|---:|']
    for x in daily:
        body.append(f'| {x["date"]} | {x["operational_added"]} | {x["tests_added"]} | {x["added"]} |')
    body += [
        '', '## Evidence and limits', '',
        f'- Roles come from module docstrings/leading comments. **{summary["header_absent"]} files have no such header**; the catalogue labels manually inspected body or test-declaration fallbacks instead of guessing from the basename.',
        f'- **{summary["tools_with_digest_runbook_reference"]} tools** have an exact-basename DIGEST/RUNBOOK reference. Each retained match carries a path, line and excerpt; a missing match is `[]`, not an invented quotation.',
        f'- Birth provenance: **{summary["origin_status_counts"].get("documented_incident",0)}** explicit incident/rule chains, **{summary["origin_status_counts"].get("documented_motivation",0)}** header motivations, **{summary["origin_status_counts"].get("origin_not_established",0)}** without an established specific originating incident. Every row still has its first-add subject/date/commit. A later rule citation is explicitly not proof that the later incident originally created the tool.',
        f'- **{summary["gate_executor_static"]} source files** have an identified static gate/executor call/import; **{summary["test_evidence_operational"]}/{len(operational)}** operational/helper files have observed static test evidence. Those are lower bounds: dynamic helper calls, variable-only shell paths and external callers can be missed. “Not observed” never means “not called” or “no tests exist.”',
        '- `callers.static_invocations` retains typed imports, command arguments and plan argv edges. Non-call code references are counted separately. Command argument extraction follows locally assigned names and is not path-sensitive; it establishes static wiring, not execution or branch reachability. `runtime_verified=false` on every row.',
        '- Rust rows list test declarations, Python-check target strings and spec-selector references. Cargo provides their test entry point; no historical evidence/board wrapper was executed to compile this inventory. `tests_executed_by_this_inventory=false` refers to each inventoried legacy tool, not our separately-run catalogue validation.',
        '- Source SHA256 values bind the pinned files; purpose/caller/document references point to that snapshot. Home-account components in copied excerpts are redacted. Full source remains reachable by its pinned git link. Full commit subjects are retained; first-add dates denote introduction at the current path, not a rename-following ancestry claim.',
        '', '## Five incidents → rules → tools', '',
        '| Chain | Incident | Rule and resulting tool | Evidence |', '|---|---|---|---|',
    ]
    bypath = {x['path']:x for x in rows}
    for c in data['incident_chains']:
        t = bypath[c['tool']]
        refs = []
        for label,key in [('incident','incident_evidence'),('rule','rule_evidence'),('source','source_evidence')]:
            r=c[key]
            refs.append(f'[{label}: `{r["path"]}:{r["line"]}`]({link(r["path"],snap,r["line"])})')
        refs.append(f'[first add `{t["first_commit"]["commit"][:10]}`]({REPO_URL}/commit/{t["first_commit"]["commit"]})')
        body.append(f'| {c["id"]} | {cell(c["incident"])} | {cell(c["rule"])} → `{c["tool"]}` | '+ '<br>'.join(refs)+' |')
    body += [
        '', '## Presenting this to terminal experts', '',
        'Use **one workflow slide, the five incident chains, then a three-minute offline evidence replay**. Keep the 259-row catalogue as a searchable appendix. Present operational tools separately from tests/adapters; show the growth chart only with the bulk-import caveat.', '',
        '```mermaid', 'flowchart LR',
        '  I[Inputs and provenance] --> S[Static identity / ABI / class / open-site scans]',
        '  S --> G[Native / frozen / generation gates]',
        '  G --> P[Plan + lock + transactional apply]',
        '  P --> A[Activation smoke]',
        '  A --> R[Sequential app observations]',
        '  R --> F[Captured screenshots + facts + first-fatal]',
        '  F --> C[Comparison / human image sign-off]',
        '  C --> K[Knowledge + frozen records + rule improvements]',
        '  K --> S',
        '  P --> B[Unconditional recovery for observation windows]',
        '```', '',
        'For the demo, use an already-recorded run: show `record.json` → `run_facts.py` totals, compare two saved fingerprints with `compare_runs.py`, then show a known rejected deployed-JAR comparison and its source rule. Use retained output if private inputs are unavailable. Do not demonstrate deployment, locks, installs or restarts during an expert talk. The main message is that incidents become recorded rules and repeatable checks, while screenshots remain the UI sign-off authority.', '',
        '## Reproduce and validate offline', '',
        '```sh',
        'python3 benchmark/2026-10-08-harness-tools-inventory/build_inventory.py',
        'python3 benchmark/2026-10-08-harness-tools-inventory/render_report.py',
        'python3 benchmark/2026-10-08-harness-tools-inventory/test_inventory.py',
        'cargo test --manifest-path tools/spec-checks/Cargo.toml --test harness_tools_inventory',
        '```', '',
        'The generator reads pinned git blobs/history rather than mutable checkout content; validation also verifies that the inventoried local source files match the snapshot. The report remains a dated snapshot. See `results.json` and `validation.txt` for checks actually run.', '',
        '## Complete catalogue', '',
        'Each source file has one row below. The JSON contains complete first-add subjects, all retained DIGEST/RUNBOOK references and typed callers; the table abbreviates caller lists and origin prose. **G/E** = observed static gate/executor wiring; **T** = observed test wiring/self-tests, **adapter** = test/replay source, **?** = not observed. There is no runtime-call claim.', '',
    ]
    for cat in summary['category_counts']:
        body += [f'### {CATEGORIES[cat]}', '',
                 '| Path / role source | One-sentence role | First add | Birth evidence | G/E callers | Tests |',
                 '|---|---|---|---|---|---|']
        for t in [x for x in rows if x['category']==cat]:
            p=t['path'];pe=t['purpose_evidence'];fc=t['first_commit'];br=t['birth_reason']
            # Unique names with complete paths live in JSON; table uses up to 3.
            caller_paths = sorted(set(x['path'] for x in t['called_by_gate_or_executor']['callers']))
            caller = ', '.join(f'`{x}`' for x in caller_paths[:3]) or '?'
            if len(caller_paths)>3: caller += f' (+{len(caller_paths)-3}; JSON)'
            if p.endswith('.rs'): caller = 'Cargo/spec adapters; '+str(len(t.get('contract_bindings',[])))+' selector refs'
            refs = br['digest_runbook_references']
            dre = '; '.join(f'[{"DIGEST" if "DIGEST" in x["path"] else "RUNBOOK"}:{x["line"]}]({link(x["path"],snap,x["line"])})' for x in refs[:2])
            if len(refs)>2: dre += f'; +{len(refs)-2} in JSON'
            if not dre: dre = 'DIGEST/RUNBOOK: no exact citation'
            birth = cell(br['incident_rule'] if br['status']=='documented_incident' else fc['subject'])
            birth += f'<br>{dre}'
            if br['status']=='origin_not_established':birth += '<br>Specific incident: unknown'
            test = 'adapter' if t['tests']['status']=='is_test_or_adapter' else 'T' if t['tests']['status']=='static_test_evidence' else '?'
            body.append(f'| [`{p}`:{pe["line"]}]({link(p,snap,pe["line"])}) | {cell(t["purpose"])} | {fc["date"]}<br>[`{fc["commit"][:10]}`]({REPO_URL}/commit/{fc["commit"]}) | {birth} | {caller} | {test} |')
        body.append('')
    (HERE/'README.md').write_text('\n'.join(body).rstrip()+'\n')
    print(f'Rendered {len(rows)} rows, {len(data["weekly_growth"])} weekly points, {len(daily)} daily points; no device operations')


if __name__ == '__main__':
    main()
