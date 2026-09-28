# Ad-hoc diagnostic tools (2026-09-25 outer-loop session)

Small tools written during the Toutiao interaction/latency work, rescued from a session scratchpad on
2026-09-28. Kept as written; none has a test. Board-side scripts run in `hdc shell` (toybox sh).

| File | What it does | Status |
|---|---|---|
| `wpactl.c` | Minimal wpa_supplicant control-socket client: `wpactl <ctrl-socket> <COMMAND...>`. | Tried against the board's `wpa_ctrl_*` sockets; they did not answer a shell client, so boards still switch WiFi only via the UI (OPS-RUNBOOK §2). Build with the OH SDK `aarch64-unknown-linux-ohos-clang -static`. |
| `tp_outer.c` | Re-check of #39: TPIDR_EL0 layout, `cached_pid` at +20, and which libc/linker got mapped. | Confirmed #39 (Bionic TLS layout under AOSP14 linker64). |
| `flows.py <pcap> <local-ip>` | Per-TCP-flow byte counts from a wl-netcap pcap, named by TLS SNI. | Used for the Toutiao network/feed investigation. |
| `oatver.py <files...>` | Print the oat version(s) embedded in .oat/.odex/.art files. | Quick check for the oat 247 (westlake) vs 230 (AOSP) mismatch. |
| `thread_sched_tap.sh <pid>` | schedstat of the main and vsync threads around one injected tap (`noice_tap`). | Thread id 2908 is hard-coded from one run — edit before use. |
| `thread_sched_trace.sh <pid> <ui-tid> <v-tid>` | 12 s of schedstat + wchan for two threads after a tap. | |
| `vsync_threads.sh <pid>` | CPU time of vsync/RenderThread threads over 5 s. | |
