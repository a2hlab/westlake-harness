# r11 observer.py — itemized review (current file SHAs)

Reviewed files (t4 `diagnostic-r11/`, sha256 short): `core.py ccb72548af7eb092`,
`identity.py a2ad02bec3659cf3`, `observer.py e9eb4a4f1010f773`. Offline, no board/build/device.

## Field counter-evidence folded in (resolved)
- Real identity: **parent UID = 0, child UID = 20011206, both exe sha256 `a7a358c6…`.**
- `core.py:25` now reads `e['uid']==20011206 and type(e['parent_uid']) is int and e['parent_uid']==0`
  — the earlier `parent_uid==20011206` same-UID constraint is **fixed**; the gate no longer refuses
  the genuine root-parent / app-child pair. My prior "A pass-logic" (which predated this) is
  superseded by the per-item verdicts below.
- Acceptance condition on the admission the outer supplies: `identity.parent_uid=0`, `uid=20011206`,
  `parent_exe_sha256 == child_exe_sha256 == a7a358c6…` (full 64-hex). `identity.py:56` checks each
  process status `Uid`==`[uid]*4`, so PARENT must show `0 0 0 0` and CHILD `20011206 ×4` — consistent
  with the field. Equal parent/child exe SHA is legitimate (appspawn clone) and is not rejected.

## Per-axis verdicts on the landed runtime
### A. real identity + player-slot selection — PASS-logic (both prior gaps closed)
- `observer.prepare_addresses` (41-47): reads the **player** GOT slots (player_bias+`0x472688` android,
  +`0x472490` shim), resolves `module(actual_ptr)`, and `need(winner.role==role and
  elf_address==expected)` with android `0x3b9c` / shim `0x5e48` — i.e. it proves the player's own GOT
  binds those providers before arming, and sets the bp at `winner_bias+pc`. This is the player-slot
  selection that was missing from core-only.
- `observer.module` (33-40): binds any pointer to exactly one admitted module by executable mapped
  range **and** a unique PT_LOAD bias (`len(valid)==1` else refuse) — double-mapped copies are
  disambiguated by the actual pointer, not guessed.
- Non-player filter (`on_hit` 106-111): events whose `x30` caller module role != `player` →
  `ignored_nonplayer` (raw kept, capped <16). Identity is re-verified bookended at pre-connect,
  attached-stopped, and **every** event-stop (`checked_identity`), plus `GetProcessID()==child`.

### B. hardware breakpoints — PASS-logic (strong)
- `require-hardware-breakpoint true` set **before** `ConnectRemote` (run 153 vs 157).
- `add_bp` (48-62): `breakpoint set --hardware --address …` (+`--thread-id` for returns); records new
  bp IDs even on command failure for cleanup; then `need(IsValid and IsHardware and
  GetNumLocations==1)` and `loc.IsResolved and GetLoadAddress==address`. `IsHardware()` re-checked at
  each hit (`on_hit` 98). No software fallback / step-out / expr anywhere.

### C. return-point association — PASS-logic (strong)
- `Calls.tail` refuses overlap + budgets; the `fromSurface_return` bp is **thread-scoped** (tid →
  `--thread-id`) and deleted after use; `Calls.returned` matches `(tid,sp,pc)`; `on_hit:99` enforces
  `tid==meta.tid`. Cross-event object identity emitted as `unknown`; `same_object_generation
  = UNKNOWN_NOT_TRACKED`.

### D. bounded exit / detach — PASS-logic (action + verification present)
- Deadline `min(start+120, start+(expires-now))`; SIGTERM/SIGINT → cancel; `remaining()` guards.
- `cleanup` (128-148): if no valid proc → error, never claims clean (outer owns server recovery);
  else interrupt if running, delete only `self.owned` bps, then `process detach --keep-stopped false`;
  bookended `guard.capture('after-detach')` sets `verified = detached ∧ bps_deleted ∧ tracer_pid==0 ∧
  state∉T/t`; `outer_recovery_required = not verified`. Status `OBSERVATION_ONLY` only when verified;
  `playback='UNKNOWN_NOT_TESTED'` always — never a playback PASS. No global hdc/server kill.

### object decode — PASS (unchanged)
`core.wrapper` magic-gated (`+0`=`0x5f776e64` → `+0xc8`=`0x414e5731` → `+0xc0` handle≠0); any
miss/exception ⇒ `class='unknown'` typed reason; success `class='AdapterAnw_layout_matches'`. Raw
registers emitted before classification (`on_hit` 100-103), so `unknown` still carries evidence.

## Residual substantive items (conditions, not blockers)
1. `prepare_addresses:42` `need(len(biases(player))==1)` — a **double-mapped player** instance would
   be refused (→ no observation / unknown), not selected. Conservative and safe; note it so a null
   result is read as "player ambiguous," not "no calls."
2. All HW-slot allocation, attach permission, and `TracerPid` are only **provable on execution** —
   the receipt's `IsHardware` results, `connect` rc, and after-detach proof are the evidence; until
   then B/D are PASS-**logic**, not PASS-on-device. Human review (t6) owns the on-device receipt and
   the winner/object truth.
3. `winner`/object are only trustworthy for events that passed the non-player filter **and** whose
   `module()` bias was unambiguous; a `winner.classification=='unknown'` tail-call re-raises (120
   `self.emit(event);raise`) → recorded then bounded-exit. Correct (no guessed winner).

## Bottom line
On the current SHAs the observer is **method-conformant across A–D** (both earlier gaps and the UID
defect resolved). Outstanding is purely on-device proof (HW slots, attach, TracerPid) + human review
of the actual winner/object/playback — un-collected stays `unknown`.
