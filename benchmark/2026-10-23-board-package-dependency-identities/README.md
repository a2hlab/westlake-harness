# T119 — 5cd dependency identities and host UID (read-only, 0.8 s of 90 s)

**Host identity.** `held` returned rc 1. Boot ecb84d86, host `org.westlake.imehost` pid 5074 (birth 9930) and Uid/Gid 20011300 (all four fields) were identical before and after the read. There were no device writes and no implementation content was read.

## startup.env declared SHA vs actual SHA
| Field | Path | Path basis | Actual = declared |
|---|---|---|---|
| HOST_SPAWN | `/data/local/tmp/a2hlab-app-c91d26bf…/host_spawn` | exact-realization `source-fingerprint.json` target | **yes** (T119 fresh stat + sha256, stable) |
| NAMESPACE | `/data/local/tmp/a2hlab-app-c91d26bf…/source_app_namespace` | same | **yes** (T119 fresh, stable) |
| MEMBERS | ROOT `members.tsv` | T116 | yes |
| START_PARENT | ROOT `real-start-parent-bounded.sh` | `members.tsv` row with the same SHA | yes (T116 hash-only, same boot) |
| DECODER | ROOT `screen-gate` | same | yes (T116) |
| PROBE | ROOT `decoder-probe.jpeg` | same | yes (T116) |
| JIT | unknown | metadata has the source `prepare_jit50.sh` only, no device target | unknown |
| REQUEST | unknown | no device path in the narrowed metadata search | unknown |

The three rows marked T116 tie a file name to a declared SHA only because the SHA values are equal; no further binding was attempted.

The private originals are at `$HOME/.local/share/westlake/board-package-dependency-identities-20261023/raw/`.
