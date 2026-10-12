# Reviewed Route B recovery integration — offline, execution disabled

R1's isolated launchers did not prove the real window-ID, namespace, JIT or
host_spawn chain. This package supplies the real captured entry scripts and
guarded wrappers, preserves accepted watchdog **9763171a** byte-for-byte, and
records the remaining production prerequisites instead of manufacturing release
approval. **No board, VM, remote, deployment, signature or old-run mutation was
performed.**

## Input evidence and identity

`bindings.json` pins 17 local source objects, 4 complete archive hashes and every
proposed placement member. Originals remain unchanged. Sources are copied only
where small; large archives and the ARM64 classifier remain pinned references.

| Component | Exact source / SHA prefix | Use and limit |
|---|---|---|
| Accepted watchdog | R1 commit `c014f86102f55b51033a0e5032c90ab4af089d09`, `9763171a` | Unchanged in `payload/watchdog.sh`; all prior R1/R2 receipts remain separate |
| Owner helper | Candidate `80a263d9`; live capture `eaba972b` | Execution lines identical; copies beside each watchdog |
| Actual start-parent | Main `benchmark/2026-10-12-toutiao-recovery-readonly/followup-1406/start-parent-0.txt`, `8e1d214e` | Real imehost0 WID query/update, then source_app_namespace; preserved exact production bytes |
| Actual spawn | Same capture `spawn-0.txt`, `46337ba8` | Real host_spawn invocation, private socket and request.bin |
| Original JIT | Local `tt-rt.tar:./prepare_jit50.sh`, `ad115b0b` | Namespace cache preparation: nonsymlink checks, mkdir, cache-only chown/chmod and readback; no data rotation |
| Native stage | Local `tt-stage.tar`, `6b4c9528` | Namespace helper `60b89e11`, host_spawn and original request `2190ff06`; not proof of current deployed bytes |
| Original runtime | `tt-rt.tar`, `014c566e` | Full archive hash checked locally; existing live runtime/code/data is not re-extracted |
| Host HAP | `df385638` | Existing foreground imehost dependency; no reinstall |
| Original controller archive | `tt-wd.tar`, `16a72b27` | Historical input, not re-executed |
| Classifier | Wiki placement `screen-gate`, `808f58a1` | ARM64 ELF imports png_image_begin_read_from_file/finish_read/free; JPEG compatibility **not verified** |
| Runtime environment | Wiki `toutiao-placement/data/scripts/run.sh`, `4c77e323` | All original preload/WebView/network/JIT flags retained; UID-only derived template; WID must be current |

The local archive member hashes match the historical inventory in main
`benchmark/2026-10-10-toutiao-boot-slot/inventory.json`. This does not promote the
archive's old UID or template WID into a current observation. Derived JIT/run
UID=20011206 and request LE offsets312/316 are explicitly listed with before/after
hashes. Another installed UID requires a new reviewed profile; no recursive UID
reconcile/chown or user-data rewrite is performed by this package.

## Exact routing and startup order

`member_layout` binds both **old** watchdog aliases:

- `/data/westlake-demo/toutiao/scripts/watchdog.sh` and its sibling helper;
- `/data/local/tmp/operator45/selfheal48/watchdog.sh` and its sibling helper.

The separate `attempt_watchdog` execution copy and helper live under
`/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview/`. All watchdog
copies are the same976 bytes. Entry passes `TT_STATE_ROOT` to this independent
directory, plus exact boot/UID/runtime/stage/socket. Old stop, sequence, events,
instance and data are preserved. Default watchdog invocation is disarmed.

The only proposed operator entry is `payload/entry.sh`; it and both launch
wrappers require an exact authorization-file SHA pinned beside the scripts.
That file currently contains **NONE**, so the current package cannot launch.
No caller-supplied hash or execute flag substitutes for it. Future approval must
bind a new placement/plan/auth SHA; this package does not create that approval.

Entry validates expiry/current boot/61b serial, current installed host UID,
accepted candidate/helper/file identities, old stop SHA and the explicitly
reviewed format/runtime prerequisites, then waits a signed bounded duration for the user's foreground desktop tap (no aa start/touch; boot/expiry/stop guards remain). Parent selection is explicit:

1. **Existing parent**: pinned PID/birth only; no name lookup or socket takeover.
   The parent's actual environment WID must equal the current foreground imehost0.
2. **New parent**: R1 verifies its own lock first, then calls
   `start-parent-prepared.sh`. The wrapper uses the real captured start-parent
   script, waits for its private socket, and validates PID/birth, executable SHA,
   private root/mount namespace and current parent WID. Failed readiness retains
   the parent/evidence and stops; it never signals a spawner.
3. **Each child spawn**: `spawn-prepared.sh` checks the parent again, validates
   public JIT SHA **and its parent-namespace SHA/inode identity**, validates
   host_spawn/request SHA, then runs the original8-second
   `nsenter -t <parent> -m -- sh /data/local/tmp/asx/prepare_jit50.sh` before the
   exact real spawn script. Parent identity/window is rechecked after JIT.

The disabled service proposal copies the proven caller's root, setuid=true,
root/system groups, sandbox0, su domain and DUMP grants, with **no restricted
ambient-caps list**. It is a proposal, not an installed init config or evidence
that these privileges currently work. There is no eager aa start, user consent
tap, profile cleanup, U13 change, SELinux change, reboot or old overlay invocation.

## Fail-closed pending prerequisites

| Item | What is known | Still required before any new execution |
|---|---|---|
| JIT effective identity | Original source and UID-only derivative recovered | Fresh live SHA and parent namespace same-file readback |
| run.sh and window | Original flags preserved; real start-parent updates WID | Fresh installed UID, WID, parent environment and effective run bytes |
| Native stage/request | Original archive/components checked; request UID/GID-only derivative | Exact live native helpers, request bytes, socket readiness and required tool availability |
| Screenshot/classifier | Existing classifier uses PNG API; R1 requests a `.jpeg` capture name | Actual capture encoding plus decoder proof; no invented converter or assumption from suffix. Until then format approval is pending |
| Preimages/rollback | First old watchdog and root helper captured | Fresh **each-target** SHA, existence/absent, mode, UID/GID, SELinux label; second old alias/helper bytes are not guessed |
| New attempt authority | R1/R2 accepted **offline** | New reviewed placement, plan, authorization/expiry/boot policy and autonomous proof; no old no_mac_repair inheritance |

`new-plan.draft.json` gives the exact targets and phased preparation/launch/
rollback sequence. Back up all overwritten control preimages first. Rollback
requires separately reviewed exact guardian PID/birth/executable/argv stopping,
then restores only those preimages/verified additions; it never signals U13 or
the Route B parent, clears old stop, deletes data, or restarts unsafe old watchdog.
There is deliberately no live deploy/reboot/rollback transport in the preview CLI.
The active legacy overlay job must be separately disabled/rerouted for a new
autonomous attempt; merely changing its watchdog does not make its clear-stop
and data reconcile steps safe.

Scope stays **61b Plan-2 20-key + 5cd existing128 cross-check**, not61b128. The
expired `seal-run-20261012T094950`, old04d plan and old acceptance evidence remain
unchanged; no old UI signature is transferred to a new attempt.

## Offline reproduction and grading

```sh
python3 benchmark/2026-10-12-toutiao-recovery-integration/preview.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_recovery_integration -- --nocapture
agent-spec lifecycle "$WORKSPACES/westlake-harness/specs/demo-recovery-followup/t4-integration.spec.md" --code tools/spec-checks --format json
```

Default preview prints exact changes, rollback and pending facts with zero device
calls. `--execute` and authorization arguments refuse. Missing/drifted sources,
placement members, invalid HERE or out-of-scope data targets are rejected.

The new launch tests execute actual shell logic with an **explicit lexical path
relocation** to temporary directories and record both original and relocated
SHA. They do not claim unmodified binary execution on Mac. ARM native helpers,
kernel process identity/namespace, board metadata tools and capture/classifier
are recording substitutes. JIT script logic and real start-parent/spawn source
logic run; the window-ID update and namespace→JIT→host_spawn order are asserted.
Mock authorization files are labelled SYNTHETIC and exist only in temp fixtures.
No real authorization/signature is produced.

Negative tests require their exact rejection reasons for unsigned/wrong hash,
expired/wrong boot/wrong candidate, missing helper/JIT/socket, mismatched private
JIT, failed JIT, missing/stale WID and unverified capture format. They cannot
pass on an unrelated shell syntax failure. Sentinel data and old stop remain
byte-identical. Synthetic READY in a positive test is not device UI or seal PASS.
Raw first failures (fixture ticket quoting, command recording and path relocation)
are preserved; final results and source/fixture hashes are in `results.json` and
`evidence/`. The three Rust selectors cover bindings, preview and real-source
startup behavior. Production status remains **pending / execution disabled**.
