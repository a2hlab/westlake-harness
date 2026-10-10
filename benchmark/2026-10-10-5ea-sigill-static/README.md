# 5ea stopping point: loader EACCES, not an established SIGILL

## Evidence and correction first

The earlier claim “pure-base HelloWorld/ZigZag died of SIGILL” is not supported
by the retained application logs. There is no application crash PC, offending
instruction, or retrieved cppcrash in these runs. Do not turn a MUSL signal-chain
banner or its handler address into an application fatal signal / fault PC.

Across **22 failed 5ea records**, **14 have a fresh child fork**. Every one of
those 14 shows the same first stopping point: loading
`/system/android/lib64/liboh_adapter_bridge.so` returns **errno13**, in both
`default` and `westlake.sealed.child`; `LSP:LOAD_ERROR:10` then precedes
`FAIL_SEALED_PROVIDER`. The parent records **exit123** for every one. Their own
child PIDs have **0 MUSL signal4 lines**, **0 Java-entry markers**, and **0
retrieved faultlog files**. The other 8 records contain no fresh child fork;
they are stale-session retries, not eight independent native crashes.

Counterexample: noon **already-lit 5ea** HW6150 and ZZ8321 each have **4 own-PID
MUSL signal4 lines**, then **5 CHILD_CK markers** and the externally signed lit
screens. Healthy 5cd HW4432 also has 4 own-PID signal4 lines and 5 CHILD_CK
markers. Even app-owned signal4 handler activity is not by itself fatal.
Screens remain the outer review ground truth; this audit does not re-sign them.

### Exact first divergence

`phase-comparison.json` binds full original hilog SHA and 1-based lines.
`evidence/hilog-excerpts.json` retains exact selected lines, not paraphrases.

| Key | Healthy noon 5ea | Failed clean-base DEFINITIVE 5ea |
| --- | --- | --- |
| HW | PID6150, line17901 `LSP:PASS_LOAD_RESULT` | PID4375, lines17979–17980 bridge errno13; line17990 `LOAD_ERROR:10`; line17994 `FAIL_SEALED_PROVIDER`; line18008 parent exit123 |
| ZZ | PID8321, line9904 `LSP:PASS_LOAD_RESULT` | PID6535, lines10923–10924 bridge errno13; line10937 `LOAD_ERROR:10`; line10942 `FAIL_SEALED_PROVIDER`; parent exit123 (indexed in JSON) |

For both keys, the first **8 application gate events are identical**:
RAC ENTER / request receipt / hook publication / stock reply, then LSP ENTER /
precondition / manifest / PID. The ninth gate event differs as above. Both
failed children reached the stock spawn phase; late `observed_pids=[]` only
means they were absent at observation, not that fork never happened.
`ProcessSignal signum17` is the parent's child-exit notification, not SIGILL.

The 19:39 revival attempts (HW6423 / ZZ7027) reproduce this loader chain too,
but retain Boat overlays. They must **not** be represented as pure U13 runs.

## Comparison with the 5cd single-host suid experiment

The signed experiment is `a94bd245a6`, under
`$WORKSPACES/westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/boat-full128/suid-experiment/`.
Its mount delta changes only PID1 mount134: the host bind loses `nosuid`, while
SHA, mode, ownership and `appspawn_exec` label stay unchanged. Host28686 then
execs under init in the appspawn domain. This proves that experiment's **host
exec** barrier, not a remedy for all child/provider failures.

HW29164 reaches:

| Original hilog line | Observation |
| --- | --- |
| 9768 | `[N10b-JNI-OWNER] bridge/runtime preloaded in westlake.sealed.child` |
| 9769 | `LSP:PASS_LOAD_RESULT` |
| 9771 | `PROVIDER:INSTALL_RESULT:0` |
| 9772 | `PROVIDER:ENTRY_RESULT:4294965293` = signed **-2003** |
| 9773–9774 | `FAIL_PROVIDER` → `FAIL_SEALED_PROVIDER` |

Thus the **same terminal marker hides different first failures**:
5ea fails *before* provider invocation (bridge dlopen EACCES / loader10), while
5cd successfully loads the bridge/runtime and installs the provider, then fails
provider entry (-2003). **A common underlying permission mechanism is unproved**;
it is not established by the common exit123/FAIL_SEALED_PROVIDER or by nosuid.
The retained -2003 line does not identify the failing syscall/path; no seccomp,
SELinux or namespace root cause is invented here. HW29164 itself has 2 signal4
handler lines before successfully completing library preload, another negative
control for the old SIGILL diagnosis.

## Same-path, three-board comparison

`fingerprint-comparison.json`: pure-base failed 5ea, healthy noon 5ea, healthy
5cd after clean reboot, failed 5cd suid experiment, and signed 61b t3 have
**124/124 identical runtime paths and SHA values**, including bridge84695d62,
runtime18763dd4 and host2a87118e. A corrupt/different deployed bridge blob is
not evidenced by these measurements. Factory libraries outside this inventory
are not silently assumed equal.

`file-state-matrix.{csv,json}` lists the same bridge/runtime/host paths with full
SHA, label and covering **PID1 mountinfo** row, source SHA and snapshot boot.
It deliberately separates time/boot domains:

- Noon healthy 5ea, earlier healthy 5cd and seal-pre 61b capture bridge/runtime
  as `system_lib_file`, host as `appspawn_exec`; covering PID1 mount rows are
  `rw,relatime`, without `noexec`/`nosuid`.
- Failed pure-base 5ea has matching ELF SHA, but no contemporaneous retained
  structured snapshot proving its child's labels/mount flags. These fields are
  **unknown**, not borrowed from noon or the later Boat run.
- Failed 5cd host-only experiment: bridge/runtime covering rows remain
  `rw,nosuid,nodev,noatime`; host row is `rw,nodev,noatime` after the single
  remount. Bridge/runtime labels in that exact run are **unknown**. Their earlier
  healthy labels do not establish the experiment's child view.
- Later failed 5ea Boat-retained snapshot: bridge8ab85446/runtimeadc125f4 have
  `system_lib_file` and captured `rw,relatime` rows; host remains2a87118e. It is
  separate evidence, **not** the 187/846 pure-base state. Two overlaid runtime
  mount rows are preserved instead of guessing which is visible from a child.

Neither a shell/PID1 label nor a mount row alone proves the failed child's view.
Failed 5ea tries the exact absolute bridge path in `default` and
`westlake.sealed.child`; failed 5cd reports successful preload in the same named
sealed namespace. A namespace name is not a Linux mount namespace identity.
The captured pre-app states also differ in launcher context: 61b's existing
host is recorded in `su`, whereas no appspawn-x exists yet in 5ea's after-reboot
snapshot. This is context, not a demonstrated cause of EACCES.

## Snapshot comparability: no false absence claims

Fresh `board_state_diff.py` outputs are retained unmodified in
`.artifacts/snapshot-diffs/`; SHA, argv, exit, incomplete fields and compact
results are in `snapshot-comparison.json`.

| Pair | Plan / tool exit |
| --- | --- |
| Noon healthy 5ea → late failed 5ea | different plans; **rc3 NOT-COMPARABLE** |
| Healthy 5cd → late failed 5ea | different plans; **rc3 NOT-COMPARABLE** |
| 61b seal-pre → late failed 5ea | different plans; **rc3 NOT-COMPARABLE** |
| Same-plan 5ea revival before → after | matching1d89 plan; **rc1 incomplete**, missing `tr` in 3/2 proc_environ captures |

No original capture is rewritten to force equal plan SHA, and no normalized
known-unavailable snapshot is promoted to raw full PASS. Individual common-path
observations remain usable with their raw pins; cross-plan absence of labels,
SHA or bind targets is **scope**, not drift. In particular the earlier “27
route-a libraries missing” claim from a no-plan snapshot remains withdrawn.

## Remaining causal evidence and disposition

`missing-evidence.json` is the minimal read-only checklist: same-plan snapshots
on all three boards; same absolute path SHA + `ls -lnZ` (including ancestors and
source), PID1 **and host/child** mountinfo and attr/current, exact boot binding,
retained permission-denial/fault logs. No app is started, no namespace is
created, no board is changed, and no lock/window is requested by this report.
A vanished child cannot be retrospectively sampled: if existing retained
child data are absent, a new approved observation window is required, not an
invented backfill. New live snapshots also cannot establish yesterday's state.

**Conclusion:** replace the DIGEST SIGILL attribution with the observed
bridge-dlopen errno13 → LSP loader10 → sealed-provider rejection → exit123.
Why only that 5ea boot fails remains **unresolved** at the file-label / child
mount / execution-domain / namespace path layer. Do not reflash, re-copy
identical runtime libraries, or prescribe a nosuid/label change from this static
evidence. The 5cd -2003 failure is a later-stage comparison, not a proven same root.

## Reproduce (local only)

```sh
python3 benchmark/2026-10-10-5ea-sigill-static/audit.py
python3 -m unittest discover -s benchmark/2026-10-10-5ea-sigill-static -p 'test_*.py' -v
```

Original raw logs remain in their persistent worktree directories and are
pinned in JSON; large raw snapshot diffs are not added to the landing list.
Evidence status is verified for the observed stopping chain, partially for
three-board state comparisons, and unknown for the precise access-denial cause.
