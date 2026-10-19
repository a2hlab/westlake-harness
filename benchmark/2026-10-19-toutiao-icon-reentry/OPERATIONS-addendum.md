# OPERATIONS addendum — r2 arm / generate / apply / rollback (offline-prepared, 2026-10-19)

Purpose: cut on-site serial time for the outer P0 board window. Everything below was
derived offline from the persisted r1 transaction and the real deploy tool; **nothing here
was executed by this lane**, and r2 is **not** claimed board-ready (cx-seal ACCEPT on
`59bee0b7` is offline; outer adoption fixes `entry=/proc` production path only).

## 0. Verified starting state (from receipts, not memory)

| item | value | source |
|---|---|---|
| r1 plan | ROOT `…/icon-manual-20261019-r1`, origin boot `6944c37e…`, plan sha `4163b09f…`, 19 files | `$HOME/.local/share/westlake/toutiao-resume-20261019/icon-manual-plan-r1/plan.json` |
| r1 before.cfg | `1589c9f2…` (973 B) = the **sealed original** cfg (`baseline/original-toutiao.cfg` has the same sha) | plan-r1 + `benchmark/2026-10-19-toutiao-icon-deploy/baseline/` |
| r1 after.cfg | `918cdde9…` (977 B): only `services[0].path[1]` → r1 `boot-entry.sh` | plan-r1 |
| apply-r1 | `PLACED_REQUIRES_NEW_BOOT`, 68 receipts rc 0, cfg `918cdde9…` written | `icon-manual-apply-r1/result.json` |
| rollback-r1 | **`CFG_RESTORED` on boot `f59c05dd…`**, cfg back to `1589c9f2…`, `runtime_changed:false` | `icon-manual-rollback-r1/result.json` |
| ⇒ board cfg now | **`1589c9f2…`** → entry points at the sealed `r1-9763171a-preview/boot-entry.sh` again | rollback-r1 step 004 `ICON_CFG_OK 1589c9f2…` |
| r1 ROOT on board | still present (evidence; **never delete**) | apply-r1 step 003 identity `66352:499283` |
| r2 payload (this tree) | `candidate-payload-r2/`, ROOT `…/icon-manual-20261019-r2`, 22 files / 16 members, **disabled** | `candidate-payload-r2/generation.json` |

Consequences that save a round trip on site:

- `prepare.py --before` for r2 must be the **current board cfg = `1589c9f2…`**. Use the
  pulled copy or `icon-manual-plan-r1/before.cfg` (identical bytes); do **not** use r1's
  `after.cfg`. `prepare.py` enforces `services[0].path == sealed OLD_ROOT/boot-entry.sh` on
  the before image — only the sealed cfg satisfies it.
- `deploy.py --execute` guards the live cfg against `before_sha256` and requires the new
  ROOT to **not exist** (`test ! -e <root>`). r2 uses a fresh root, so r1's presence is
  irrelevant; if the live cfg is not `1589c9f2…` the apply refuses before writing.
- `deploy.py --rollback` only accepts a live cfg equal to the plan's before or after sha
  ("foreign cfg, rollback refused") and restores the before bytes. For r2 that is the
  sealed cfg — a rollback returns the board to the sealed entry, not to r1.

## 1. Generate (host, armed; outer only)

```sh
OUT=<new absolute dir, must not exist>
sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh \
  --out "$OUT" \
  --root /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2 \
  --enable --approved-by 'outer(codex)'
```

Expected in `$OUT/generation.json`: `armed:true`, `startup_enabled:1`,
`payload_files:22`, `members:16`, `candidate_watchdog_sha256` =
`41f1bf653f4becf3bb40a1a754f8e0c35520ce9fa6a0eb3da84c01ef96e64a28`.
`members.tsv` sha is **identical** to the committed disabled build
(`bff9e4377602ebd333bdc3833de0660601d2345afb092a07e4e49ea4443f099a`) because arming
changes only `startup.env`; `startup.env`/`startup.expected.sha256` differ from the
disabled build by design.

Pre-prepare checks (host, seconds):

```sh
diff <(sed 's/ .*//' "$OUT/payload/members.tsv") \
     <(sed 's/ .*//' benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload-r2/payload/members.tsv) && echo MEMBERS_SAME
grep -E "STARTUP_(ENABLED|APPROVED_BY|SERIAL)=" "$OUT/payload/startup.env"
# expect: ENABLED='1'  APPROVED_BY='outer(codex)'  SERIAL='61b0657200000000000000000324012c'
```

## 2. Prepare (host, no device)

```sh
BEFORE_CFG=<pulled current cfg>          # must hash to 1589c9f2…; plan-r1/before.cfg is byte-identical
ACTUAL_BOOT=<boot_id read from board at window start>
PKG=<new absolute dir, must not exist>
python3 benchmark/2026-10-19-toutiao-icon-deploy/prepare.py \
  --payload "$OUT/payload" --before "$BEFORE_CFG" --boot "$ACTUAL_BOOT" --out "$PKG"
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py --plan "$PKG/plan.json"   # preview, no device calls
```

Expected `plan.json`: `root` = r2 ROOT; `before_sha256` = `1589c9f2…`; `after_sha256` =
new (sealed cfg with only the entry path → `…/icon-manual-20261019-r2/boot-entry.sh`);
`files` = **20 rows** (r1 had 19: 15 members + `boot-entry.sh` + `members.tsv` +
`startup.env` + `startup.expected.sha256`; r2 adds the 16th member `exit-verdict.sh`).
The payload *directory* holds 22 files because `recovery.cfg` and `rollback-inert.cfg`
are reference artifacts that `prepare.py` does not package.

Diff against r1's plan (what changed, nothing else):

```sh
R1=$HOME/.local/share/westlake/toutiao-resume-20261019/icon-manual-plan-r1
diff <(python3 -I -c 'import json,sys;[print(r["name"],r["sha256"][:12],r["mode"]) for r in json.load(open(sys.argv[1]))["files"]]' "$R1/plan.json") \
     <(python3 -I -c 'import json,sys;[print(r["name"],r["sha256"][:12],r["mode"]) for r in json.load(open(sys.argv[1]))["files"]]' "$PKG/plan.json")
```

Expected delta only: `watchdog.sh` (`bd2f83be`→`41f1bf65`), `entry.sh` (new watchdog sha
pinned), `config-common.sh` (ROOT r1→r2), `members.tsv`, `startup.env`,
`startup.expected.sha256`, **+ `exit-verdict.sh` (new)**. Unchanged: `reentry-common.sh`
`43d7b073`, `reentry-seams.sh` `febc7094`, `route-b-owner.sh` `6bce7c3c`, all base
launch/readiness/capture members. `diff "$R1/before.cfg" "$PKG/before.cfg"` must be empty;
`diff "$R1/after.cfg" "$PKG/after.cfg"` must differ **only** in the `-r1`/`-r2` path suffix.

## 3. Apply (outer, holding the exact 61b board lock)

```sh
RUN=<new absolute dir>
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py \
  --plan "$PKG/plan.json" --execute --out "$RUN"
```

Expect `result.json` `status: PLACED_REQUIRES_NEW_BOOT`, `cfg_sha256` = plan
`after_sha256`, `runtime_changed:false`, every step rc 0 (r1's 19 plan files took 68
receipts; r2's 20 plan files → ~71). Placement starts nothing; the existing service
`westlake-u13-toutiao-overlay` on its existing trigger reads the new entry on the next boot.

Then the fresh boot (the only execution path): reboot → first manual host tap → guardian.
Acceptance remains spec scenario 5: controlled exit → `AWAITING_REENTRY` → real
desktop→icon tap → feed screenshot + identity + capture receipts; and reboot → tap → feed.

## 4. Rollback (outer)

```sh
RB=<new absolute dir>
python3 benchmark/2026-10-19-toutiao-icon-deploy/deploy.py \
  --plan "$PKG/plan.json" --rollback --execute \
  --boot "$CURRENT_BOOT" --apply-receipt "$RUN/transaction.json" --out "$RB"
```

Expect `status: CFG_RESTORED`, `cfg_sha256` = `1589c9f2…` (sealed). r1 and r2 ROOTs stay
on the board as evidence; a cfg restore does not touch a running guardian — stop/reboot
sequencing is explicit outer work. Never run two guardians.

## 5. Not covered here (unchanged rules)

No same-boot attach; never clear the socket or signal the parent; not a crash fix; the
payload's `recovery.cfg` is a reference artifact and is not installed.
