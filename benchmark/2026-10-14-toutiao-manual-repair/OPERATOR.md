# 5cd owner experiment (outer execution only)

The experiment changes **one directory's UID/GID only**, from0:0 to20011300:20011300. It preserves its inode,0755,appdat label and all contents. It neither creates app_webview nor recursively changes anything. The separately delivered JIT51 candidate is NOT installed by this experiment. The current frozen JIT50 can remain for this key test.

Outer holds the existing board lock and current authorization, bounded30min. No61b commands. Use a fresh local evidence directory and real native HDC path. Renderer is offline; generated `execution_enabled:false` is an operator command card, not a board_run plan or authorization.

```sh
B=benchmark/2026-10-14-toutiao-manual-repair
python3 "$B/render_owner.py" preflight --boot c9436daa-b3ca-44dc-985f-9ee03445567a --parent 5257 --birth 8214 --hdc "$HDC" --out "$OUT/preflight.command.json"
```

Execute the exact `argv` from command JSON using the existing outer transport, persisting original stdout/stderr/host rc/time. Require host rc0 **and** explicit `OWNER_REMOTE_RC=0` **and** one VERIFIED observation JSON. Save that JSON verbatim as`preflight.observation.json`. The body rechecks current boot, parent birth/binary, host owner, private namespace, physical/namespace same directory inode and no children across all parent threads. It rejects unexpected metadata and an existing app_webview.

```sh
python3 "$B/render_owner.py" apply --boot c9436daa-b3ca-44dc-985f-9ee03445567a --parent 5257 --birth 8214 --hdc "$HDC" --observation "$OUT/preflight.observation.json" --out "$OUT/apply.command.json"
```

Execute/save the same way; save`apply.observation.json`. A nonzero or missing marker is failure even if HDC returns0. An intent without a VERIFIED receipt requires read-only observation of the exact directory before any retry; never claim rollback already occurred.

## Recovery / UI is a separate step

Current guardian is absent. The frozen entry waits for an initial foreground host, then refuses an existing socket; the watchdog stops after3attempts. Clicking imehost again does **not** recreate a guardian or send a new host_spawn request. Do not run old boot-entry/entry, overwrite old attempt/sequence/state, or kill the parent.

For this experiment the outer used `evidence/single-spawn.command.json`: one original JIT50 then one exact host_spawn invocation, after parent/birth/boot/no-child/WID29 and source SHA guards. No new guardian or control directory was required. It returned pid17175/rc0 according to the actual outer receipt. This does not fix durable desktop reentry; p4 owns that separate branch.

The failed apply's desired-string parsing did not pass readback. Its owner change was independently reconciled using `evidence/reconcile.command.json` (read-only), bound to original preflight plus failed command/stdout SHA. Preserve both failures, including the initial unsupported children interface. For rollback pass the VERIFIED reconcile observation in place of apply.observation.json; the renderer accepts only exact same after metadata. Reconcile does not rewrite the failed apply to PASS.

## Rollback (owner only)

End the owned candidate child through the existing UID/birth-scoped outer cleanup if required; never signal parent. Once no child consumes the directory:

```sh
python3 "$B/render_owner.py" rollback --boot c9436daa-b3ca-44dc-985f-9ee03445567a --parent 5257 --birth 8214 --hdc "$HDC" --observation "$OUT/apply.observation.json" --out "$OUT/rollback.command.json"
```

This expects the same inode/mode/label with20011300:20011300 and changes only owner back to0:0. Any application-created app_webview/files remain; no deletion or recursive operation. Thus rollback restores the experimental metadata only, not newly created user state. Boot/parent changes require separate fresh review; do not regenerate original before from a foreign current value.
