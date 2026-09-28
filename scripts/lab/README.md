# Lab scripts (versioned mirror of `westlake-inputs`)

The board / VM / build scripts the campaign runs every day live in `~/orca/workspaces/westlake-inputs`,
which is **not a git repository**. This directory is a byte-identical, versioned copy of its
`tools/*.{sh,py,c}`, `env-mac.sh`, `mise.toml` and `toolshim/`, taken 2026-09-28.

The live copy stays where it is: 14 of these scripts hard-code `westlake-inputs/` paths, and the VM
`a2hlab` and the inner-loop agents call them there. Edit the live copy, then re-sync:

```
W=~/orca/workspaces/westlake-inputs
cp -p $W/tools/*.sh $W/tools/*.py $W/tools/*.c $W/env-mac.sh $W/mise.toml scripts/lab/
cp -p $W/tools/docker/Dockerfile scripts/lab/docker/
cp -pP $W/toolshim/* scripts/lab/toolshim/
```

Not mirrored: `tools/apkeep-*` (downloaded binaries), `tools/scratch/`, `__pycache__`, the APK and corpus
data at the top of `westlake-inputs`, and `HANDOFF.md` (a 2026-09-24 session hand-off; its pitfalls are
in `.octos/OPS-RUNBOOK.md`).

| Script | What it does |
|---|---|
| `board_setup.sh <serial>` | Fresh OH 6.1.0.31 DAYU600 → clock from the Mac, screen timeout, unlock, install the host HAP, stage the framework (holds the undocumented stage arguments). |
| `hdc_mac.sh` | hdc for tools running inside the OrbStack VM: forwards to the Mac's hdc, base64-encoding cwd/argv so board paths survive. |
| `baseline_run.sh` | Launch app keys on one board one at a time; re-front the host; screenshot. |
| `ttdrive.sh <serial> <run> {front,vt,tap,consent,shot,alive,log}` | Drive one run through the bridge's in-process tap channel. |
| `toutiao_accept.sh` | Toutiao "usable" acceptance on one board. |
| `stop_by_pattern.sh <regex>` | Stop processes by command line without matching itself (`pgrep -f` matches its own shell). |
| `rebuild_all.sh`, `build_runtime.sh`, `build_phase*.sh` | Board-free rebuild of the runtime in the VM, resumable. |
| `dockbuild.sh {image,run,cc,check}` + `docker/Dockerfile` | Build in OrbStack amd64 docker containers instead of the VM shell: the VM filesystem is bind-mounted in place via `/mnt/machines/a2hlab` (incl. the author path), so the build scripts run unchanged; outputs are byte-identical to the VM's and several containers can build in parallel. Board work stays in the VM. |
| `map32bit_shim.c` | `LD_PRELOAD` shim that makes host dex2oat work under Rosetta (which ignores `MAP_32BIT`). |
| `static_pipeline.py`, `*static100*.py` | Hash-validated static scan → gap map, no device. |
| `board_acks.py`, `watch_inner_negative.sh`, `watch_pane_idle.sh` | Outer-loop board and inner-loop watchers. |
| `zig_prefetch_build.sh` | Build herdr when Zig's HTTP client fails through the proxy. |
| `env-mac.sh`, `mise.toml`, `toolshim/` | macOS host environment: `cc`, `readelf`, `sha256sum` shims and the pinned JDK. |

`adhoc/` holds small diagnostic tools rescued from a 2026-09-25 session scratchpad (see its README).
