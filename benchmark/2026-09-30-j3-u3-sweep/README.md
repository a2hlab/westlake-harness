# J3 on U2, two-board sharded sweep: 25 lit, no regression → U3 = U2 + J3

**State** U2 (N2 `51a78bde`, installer FZ-001) with JAR J3 `75c2068c` bind-mounted over J2 on 5ea and 61b
(66 keys, 33/33; `keys-5ea.txt`/`keys-61b.txt`). Single variable against U2: the JAR.

| board | facts TOTAL |
|---|---|
| 5ea | `TOTAL keys=33 screenshots_captured=60/60 alive_t5=16 alive_t20=16` |
| 61b | `TOTAL keys=33 screenshots_captured=66/66 alive_t5=16 alive_t20=15` |

Both boards: `RUNTIME fingerprint=0b81cdbe0ed9` (U2's plus the JAR), `FROZEN checked=4 violations=0`.

Read from `evidence/sheet-<board>-t20.jpeg` (case-insensitive key order, 7 per row): **25 apps show their own UI
at t20** — all 24 of U2 plus fd-noice (its own "欢迎" intro, `evidence/fd-noice-5ea-t20.jpeg`; lit once in r16,
so the cumulative count stays 27). uhabits is white again (intermittent, see the U2 report).

The two J3 targets, from hilog:
- **fd-api**: the alias-target theme fix works — `[B8-ALIASTHEME] com.termux.api.activities.TermuxAPIMainActivity
  theme re-resolved 0x1030237 -> 0x7f120252` — and the AppCompat-theme crash is gone; the activity now fails later
  (`RuntimeException: Unable to start activity … TermuxAPIMainActivity`). Wall passed, next wall.
- **NewPipe**: the full cause chain of the in-process PlayerService bind is finally visible:
  `[B8-AMB] caused by: java.lang.IllegalStateException: Platform signature not found` — the synthesized
  `android` package carries no signing info. That is J4's target.

**Decision.** No regression (U2's 24 all lit) → J3 overlaid on 5cd as well; the unified state is **U3 = U2 + J3**
on all three boards (2026-09-30 17:5x, verified by shell and appspawn-x root SHA `75c2068c`).

**Rule kept.** A diagnostic-only JAR change still goes through a full sharded sweep before it joins the unified
state; here it also surfaced the next NewPipe wall that three earlier rounds could not name.

Raw runs (not committed): `runs/j3-5ea/`, `runs/j3-61b/`.
