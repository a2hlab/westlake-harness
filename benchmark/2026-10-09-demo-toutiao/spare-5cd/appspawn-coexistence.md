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
