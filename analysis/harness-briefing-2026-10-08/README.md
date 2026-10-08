# Harness briefing for terminal OS experts (2026-10-08)

A talk and reading pack in four parts: the harness's philosophy, its tools (where they come from, how they are
classified and what each does), how OctoLoop drives the lanes, and how the harness evolves (process, tools and
deterministic knowledge).

**What was wrong first.** cx-t0 fact-checked the first draft adversarially
(`benchmark/2026-10-08-briefing-factcheck/`). Of 185 assertions it found 11 wrong, 45 misleading and 7 unverifiable.
The most important errors:

| Draft said | Correct |
|---|---|
| U9 lit 114/166 | 115/166 final |
| U3 lit 27/66 | 25/66 for that sweep; 27 was cumulative |
| 384 benchmark dirs | 379 tracked at the snapshot |
| sysconf moves 0 keys | true on the U13 base only; DIGEST 791 projected +4 on U14; the 10-08 U14-hilog recheck gives +2 certain, +3 at most (mcdonalds is an early SIGILL) — gated on the user |
| "115 lit keys also have two copies" | bridge ×2 in 115; runtime ×2 in 85, ×1 in 30 |
| "86 Rust tests" | 86 modules, 310 `#[test]` |
| "the same mistake never happens twice" | contradicted by FLAW-008 recurring 8 times |
| two demo commands | were placeholders |

Every finding was corrected. Every number now states its unit, snapshot and cutoff.

## Rules this sets

1. A number in a talk carries its unit and cutoff:
   - snapshot `aa948b8c9a` for repository counts;
   - board line counts at 2026-10-08 21:15 (21,907 lines).
2. A superseded conclusion is shown with its history, not just its latest value. Example: the sysconf prediction
   was 0 on the U13 base, projected +4 on U14, and +2..3 once rechecked against U14 hilogs. A stale cluster table is how the outer loop once approved an
   already-deployed fix.
3. A "verbatim" demo must be runnable as shipped. `demo.sh` pins the retained run directories and needs only
   `WORKSPACES`.
4. "Screenshots are ground truth" is scoped to on-screen state. The U12 crypto counterexample (154/174
   process self-tests failing behind clean screenshots) is part of the talk.

## Files

| file | what it is |
|---|---|
| `briefing.zh.md` | long-form script/reading doc. Sections: one-page summary; 8 principles with incidents; tools (origins, 10 categories, 5 incident→rule→tool chains, release pipeline); OctoLoop (roles, board grammar, dispatch, sentinels, locks, landing, escalation, a worked round); evolution (loop, FLAW table, five knowledge forms, gates born from errors, lit curve with units); six stories; demo; the five questions experts are most likely to ask; discussion; appendix of numbers with commands |
| `build_deck.py` | the 29-slide 16:9 PPTX. Shape-drawn charts render identically in PowerPoint, Keynote and Quick Look. There are no speaker notes, because python-pptx notes slides hang Quick Look. |
| `md2html.py` | md → HTML. The PDF is rendered by `chrome --headless --print-to-pdf`. |
| `demo.sh` | the three-minute offline replay: `run_facts` (facts), `compare_runs` (7 variables, hypothesis verdict) and `check_frozen` (8 entries, 34 checked, 0 violations). All three exit 0 on the retained U14 stage-A runs. |
| `arch.png`, `stk-u13.jpg`, `stk-u14.jpg` | the architecture slide image and the fd-stk U13-vs-U14 t20 pair (copied from the signed runs) |

Outputs (PPTX, HTML, PDF) are written to `$WORKSPACES/westlake-inputs/reports/2026-10-08-harness-briefing/` and
are not committed.
