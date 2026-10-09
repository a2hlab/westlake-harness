# Do B's appspawn-x and U13's appspawn-x contend? — static verdict: NO resource contention; they coexist (cc-t3 #91)

The on-board observation ("U13 appspawn-x got replaced when B overlaid") raised a key risk: the demo board must run
Toutiao **and** 128 apps together. Static analysis of the two binaries + B's launch script shows **no contention on
socket, service registration, or lock** — they can coexist. The only real clash is a **process-NAME collision**, an
operational/tooling hazard (not a runtime conflict), with a cheap isolation fix.

## The two appspawn-x are different binaries
| | B's (Toutiao RT) | U13's (route-a) |
|---|---|---|
| binary sha256 (prefix) | `a7a358c6…` | `b7205719…` |
| symbols | `appspawnx::SpawnServer` (custom westlake) | `OHOS::AppSpawn::AppSpawnDfUtils` (OH-native) |
| how started | `run.sh` → `exec /data/local/tmp/asx/appspawn-x --socket-name A2HSourcec91d26bfb4db4fd5a002` (plain process under `source_app_namespace`, in B's mount namespace) | begetctl-managed service (RUNBOOK #12), OH-standard |
| listen socket | `/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002` (unique per-bundle, from run.sh) | OH-standard AppSpawn socket (`/dev/unix/socket/AppSpawn`); binary refs `/system/bin/appspawn`, `nativespawn`, `nwebspawn` |
| registers a service? | **no** — not a begetctl/init service; writes only `/data/local/tmp` | **yes** — the unified-state begetctl service |

## Contention analysis
- **Socket: NONE.** B binds a **unique** abstract socket `A2HSourcec91…` (its bundle suffix); U13 uses the OH-standard
  AppSpawn socket. Different names → no `bind()` clash, neither steals the other's socket.
- **Service name (begetctl/init): NONE.** B's appspawn-x is a plain `exec`'d process from `run.sh` (via
  `source_app_namespace`); it does **not** register a begetctl service. U13's is the begetctl service. B never competes
  for the service slot, so it cannot "stop"/"restart" U13's service.
- **Active kill: NONE.** B's `run.sh` contains no `rm …/socket`, no `begetctl stop_service`, no `kill`/`pkill`/`pidof` —
  it only `exec`s its own appspawn-x. So B does not actively tear down U13's appspawn-x.
- **Lock: NONE shared.** B's runtime state is under its own `/data/local/tmp/asx` + crash42 dir; U13's service lock is
  the begetctl/init one. No common lock file.

**Verdict: B's and U13's appspawn-x do NOT contend for socket, service, or lock — they can run side by side.** The on-board
"replacement" I saw was **not** a resource conflict. Most likely explanation: U13's appspawn-x is effectively
spawn-on-demand/idle-exit, so when no U13 app was spawning (my icon-tap never actually launched a route-a app — see
`facts-5ea-coex.txt`), only B's appspawn-x showed up; and `pidof appspawn-x` conflates the two because of the name clash
below. The real coexistence test (launch U13 apps via `board_run`) will spawn U13's appspawn-x on demand.

## The real issue: process-NAME collision ("appspawn-x")
Both processes present comm/argv[0] = **`appspawn-x`** (B from the `exec` basename; U13 the route-a binary). So every
**name-based** tool conflates them: `pidof appspawn-x`, `pkill appspawn-x`, and RUNBOOK #12's "never kill appspawn-x" rule
cannot tell B's orphan from the live U13 service. This is what made my earlier observations ambiguous and is the actual
hazard for a demo board.

## Minimal isolation (keep them unambiguous)
1. **Manage by exe-path / socket, never by process name** (already applied): `rollback_toutiao.sh` step 2b reaps B's
   spawner by **exe path with `(deleted)`**, never by bare name, so it can never hit the live U13 service. Any lane touching
   "appspawn-x" on a demo board should match `readlink /proc/<pid>/exe` (B = `…/asx/appspawn-x`; U13 = its own path) — not
   `pidof appspawn-x`. RUNBOOK #12's rule should be scoped to the U13 begetctl service by exe/service identity.
2. **(Recommended, low-effort) give B's spawner a distinct comm name** so even name-based tools separate them: `exec` it via
   a renamed path, e.g. `cp/ln appspawn-x asx-spawner` and `exec /data/local/tmp/asx/asx-spawner --socket-name …` in
   `run.sh`. Then `pidof appspawn-x` returns **only** the U13 service and B's is `pidof asx-spawner`. (Caveat: if the binary
   `prctl(PR_SET_NAME,"appspawn-x")`s internally — it makes several `prctl` calls and carries an `AppSpawnX` string — the
   kernel comm may still be forced; verify on-board after the rename, and fall back to exe-path management if so.)

**Bottom line for the demo board**: Toutiao's self-contained spawner (unique socket, own namespace, non-service) coexists
with the U13 appspawn-x service that lights the 128 apps — no socket/service/lock fight. Keep process management
exe-path-based (step 2b) and optionally rename B's spawner. The empirical 10-key coexistence is re-run via `board_run` in
the dedicated window (see PROGRESS).

---

# On-board verification (5ea, U13) — CORRECTION + the complete picture

Ran it on live U13. The socket/service analysis above holds, but the on-board behaviour adds the decisive piece: the
process-NAME collision is **not** a mere tooling nuisance — it **destabilises** the U13 service.

## What the exe paths finally showed (the two DO have distinct identities)
- **U13 appspawn-x = `/system/bin/appspawn-x`** (the begetctl service; restored with `begetctl start_service appspawn-x`).
- **B appspawn-x = `/data/local/tmp/asx/appspawn-x`** (B's RT, in `source_app_namespace`'s private mount namespace — host
  `/data/local/tmp/asx` does not even exist / `mount|grep asx` empty; unique socket `A2HSourcec91…`).
- They briefly ran **together** (e.g. `14558` B + `16043` U13 both alive) → distinct binaries/paths/sockets, so there is
  **no fundamental socket/service/lock contention**.

## But coexistence is UNSTABLE because of the name collision
Repeatedly, when B was overlaid, U13's `/system/bin/appspawn-x` service got **displaced** (6251/30436 → gone; 14196 → gone;
16043 → gone), each time while B's `/data/local/tmp/asx/appspawn-x` churned (its watchdog aggressively restarts
toutiao + spawner). `begetctl start_service appspawn-x` brings U13's back, and it is **stable again once B is rolled back**
(verified: post-rollback `17666 /system/bin/appspawn-x` steady). So:
- **Root cause**: both processes present comm = `appspawn-x`. begetctl/init service management keys on that name, so B's
  churning `appspawn-x` process is **conflated with the U13 `appspawn-x` service**, and B's cycling knocks U13's out.
- This is why the earlier observation looked like "B replaced U13's appspawn-x": it did, via the name collision at the
  service-manager level, not via a socket/binary fight.

## Required isolation (now mandatory, not optional) for the demo board
1. **Rename B's spawner to a distinct process name** so begetctl/init only ever manages the real U13 `appspawn-x`:
   in `run.sh`, `exec` a renamed binary (e.g. `cp appspawn-x asx-spawner; exec /data/local/tmp/asx/asx-spawner
   --socket-name A2HSourcec91…`). Verify on-board that `/proc/<pid>/comm` is `asx-spawner` (the binary makes `prctl` calls +
   carries an `AppSpawnX` string — if it force-sets comm, patch that too). Then `pidof appspawn-x` = only U13's service, and
   B's churn can no longer confuse it.
2. **Dampen B's watchdog restart churn** (it restarts toutiao+spawner aggressively) so even a residual name overlap doesn't
   repeatedly poke the service manager.
3. Keep **exe-path management** everywhere (rollback step 2b already does) — never `pidof/pkill appspawn-x`.

## 10-key coexistence launch — NOT run this window
Because the coexistence was unstable (U13 appspawn-x kept getting displaced by B's churn), launching the 10 keys via
`bms_batch` would not have been a fair test (they need the U13 appspawn-x service up and steady). The right order is:
**apply the rename isolation first, re-verify U13 `appspawn-x` stays up with B present, then run the `board_run`/`bms_batch`
10-key sweep.** Post-rollback 5ea is clean U13 (appspawn-x `17666` stable, imehost removed, board up).

**Net**: Toutiao's spawner and U13's appspawn-x are resource-independent and CAN coexist, but the shared process name makes
it unstable today; the fix is a one-line rename of B's spawner (+ watchdog dampening). The demo board (toutiao + 128 apps)
is achievable **after** that isolation — not before.
