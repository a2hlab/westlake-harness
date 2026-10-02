# Erratum to benchmark/2026-10-03-u14-bridge-m5-m6 (f1f7cb5851)

**What was wrong.** f1f7cb5851 said "M5 alone does not move dddmodel2", and that 3 of the 13 dialog-first lit keys
(secuso memory / pin / ruler) "raise a dialog window with no Surface". It also recommended "ship M5 with the bridge
M1 (438bc948)".

Both conclusions replayed the U10.1T8 lookups. That run's runtime has **no M1**. U14 deploys the bridge on top of the
**U13 runtime 18763dd4**, whose M1 is in `android_graphics_compat_shim.o` (DIGEST 2026-10-02, line 688):
1. The compat shim's own copy of the bridge returns null for a session it did not create.
2. The shim then finds the other loaded copy of the same file with `dl_iterate_phdr`: same entry bytes, inside its
   executable segment. It calls that copy's lookup, logging `[M1-COPY]`.
3. That copy is the one that created the session, so it has it in `sessions_`.

So under U14 every dialog session, created first or not, gets its Surface:
- dddmodel2's 686, and the group-B dialogs (memory 603, pin 590, ruler 606), included.

**Corrected predictions for U14 = U13 runtime 18763dd4 + bridge e34de8ab + M5 + M6 (7daa5435):**

| key | corrected |
|---|---|
| dddmodel2 | **+1 with M5** (own dialog on top; medium, content unknown). The outer's original prediction stands. |
| 13 dialog-first lit keys | all: own dialog on top (where alive at t20); groups A/B/C behave alike. Still lit. |
| fd-mobile, fd-AppManager, termux, the 34 under_dropped keys | unchanged from f1f7cb5851 |

The "no Surface without M1" analysis (`dialog_surfaces.py`) stays valid for a runtime without M1. It is now the
expected picture **only** if the shim M1 is absent or misses: no `[M1-COPY]` line for the dialog session. The board
check: `[M1-COPY]` for each dialog session before its first draw.

The bridge-side M1 (438bc948) is not needed. The outer's decision (M1 once, in the runtime shim) is consistent with
this.

Rule: **a prediction for a single-layer swap must use the full deployed stack of the target generation** (runtime +
JAR + bridge), not the signing run's stack. Check DIGEST/FROZEN for what the other layers already fix.
