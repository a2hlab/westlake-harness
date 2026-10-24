# Ordinary host 4958 log collection card (not executed)

Use `plan.json`'s exact HDC argv through the outer's existing bounded streaming recorder: **10 seconds total; stdout + stderr at most 1,048,576 bytes**. These are host-recorder limits, not flags provided by hilog. Do not run the naked argv without those limits. Receipt destination: `$HOME/.local/share/westlake/ordinary-host-4958-20261024/collect-01/` (`argv.json`, `stdout`, `stderr`, `receipt.json`). On timeout/cap retain partial data; absent postguard is UNKNOWN. No automatic retry.

The inner command is:

```sh
hilog -P 4958 -z 2000 -L D,I,W,E,F -v epoch
```

T114 README line7 documents this exact PID-tail form with historical PID5074: rc0,987 lines. Use **no `-x`**. The new argv surrounds it with read-only boot/uptime/stat/cmdline captures and a separate remote hilog rc marker. It has not been run for4958.

T114 `wl_ime_host_lines.txt` lines23–25 record tag `A00000/WL_IME_HOST`, JSON `event:foreground` followed by `stage-event` values1/2; also preserve `created`, `window-ready`, `background` when present. Treat foreground as the ordinary callback log, not proof of click delivery latency or feed. Do not prefilter the stored output; derive event excerpts locally afterward. An rc0 containing CODE/usage errors is not valid coverage.

Compare actual first/last epoch with the existing click interval. Child22035 birth6535369 at100Hz is boot-relative65353.69s; only align to epoch with a same-boot clock/uptime anchor. The10s collection deadline is not10s log coverage. Missing old events remain unknown. No control scripts, new UI action, device call, or source modification was performed by this task.
