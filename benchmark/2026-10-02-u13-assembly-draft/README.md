# U13 assembly draft — disabled, not admitted

## Correction and identities

An unchanged count of open sites is not a production static PASS: the VLC relink changes the PC inside one unresolved-register diagnostic, and the production signature includes that text. Likewise, two newly covered N1 source findings are not two newly added binary opens. Keep these raw refusals; do not hide them with scanner normalization or self-approved registry rows.

The exact U12 base is bundle `bf6c0fb67d76f1f1d54725738b78f58d24483ceeac66087e2e801d74d1b650ee`, native manifest `2a3fac8153e080f509cd0949bc521e5e9d81ec37937c312689fb1fec2b1494df`. Do not substitute the `bd08c3f7` execution-marker variant. U12 Stage A has no confirmed regression in the outer 22:44:50 signoff, but final acceptance is pending; a confirmed regression requires outer redesign, not automatic substitution of T8.

| Identity | SHA256 |
|---|---|
| **Draft bundle** | **`473ba28da411d0dacdffaf2931490b01bd18896e8ce713d259e80c816b7e75cb`** |
| **Draft native manifest** | **`7615b424aad957518fd8884a5b0ee3b404d9a207e7ee495972dbd1fd87893dbc`** |
| Runtime, root only | `18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae` |
| VLC compat, root + route | `b2be657ca2c171dd786068e77be90d82ec3a50407df37b1ccbafef94a8db88a6` |
| Policy, root + route | `b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7` |
| **Unchanged U12 host** | **`2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e`** |

Persistent package: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-u13-assembly-draft/.artifacts/bundle`. Large ELF/JAR/image bytes and original logs stay there, not in git. Five existing targets change, **zero new native members**, zero JAR/image changes, no rebuild. Host `c2883376` is deliberately held pending McDonald's U12 result. The package/bundle flags are false and carry no window authorization; the executor remains cx-t0. No board operation or current-package mutation occurred.

## Full-package static scan

`full-package-open-sites.json` covers **116 effective ELF targets**, **99 distinct baseline/candidate ELF byte sets** (96 candidate byte sets +3 replaced baseline sets). Every target, including unchanged aliases, is represented; equal SHA bytes reuse a scan. All99 scanner commands exit0, with99 public JSON snapshots under `scans/` and original stdout+SHA in `.artifacts/raw/`. Supplemental system-ELF closure inputs are N2 inventory, not effective package deployment targets.

| Effective targets | Open sites old→new | Namespace edges old→new | Delta |
|---|---:|---:|---|
| Entire package, aliases counted | 299→299 | 19→19 | No new executable open or edge identified |
| runtime root | 197→197 | 0→0 | Exact production open delta empty;198 findings, not198 sites |
| compat root + route, each | 2→2 | 0→0 | One raw signature removed/added, unresolved-clobber PC `0x3758`→`0x3a58` |
| policy root + route, each | 0→0 | 0→0 | Empty open/edge delta |
| unchanged host | 8→8 | 17→17 | INHERIT-REPEAT0; four original INHERIT-AFTER-OPEN may-paths unchanged |

Raw DEFAULT-NS/MULTI-NS findings remain in the scanner stdout and JSON; no existing hazard was erased. The host and child are unchanged, so their existing may-paths and multi-namespace findings are not fixed by this composition. `static-checks.json` is **REJECT**, with **two REVIEW_REQUIRED target rows** for the paired compat aliases. `static-delta-explanation.json` and the two `dlext-body-*.txt` files explain the shifted diagnostic location; they are not an outer approval. Exact reviewed delta SHA is `45e215dd7193957e17d99b67e20b416dfaa6047f77225a927bab483afae12608`.

All changed artifacts have ABI/calls reports. Removed exports, signature drift and consumer breaks are0. Compat adds exactly four reviewed exports; policy adds0; runtime adds0. Runtime has **three intended named-call differences** routing existing window consumers through `oh_wm_get_native_window`; a calls report is not a zero-body-change claim. Additional checks explicitly supply all96 unique package ELF consumers to each of the three producer comparisons and return0; this is not a166-APK relocation-scope proof.

`strings-review.json` retains raw runtime3-drop/4-add and policy0-drop/2-add results. The runtime adds one92-byte M1 diagnostic, moves one embedded readelf label by0x5d, and changes two printable jump-table byte sequences (equal-length373/70 twins); donor evidence and raw rows are preserved for outer review. Policy adds only `libmedia_jni.so` and the exact resident runtime path; SoundPool/mediandk and shared SONAMEs remain. Compat raw strings0/0. No allow-list was applied.

## Native gate and admission draft

The current master registry accepts U12 **N1=53/N2=104**. The draft has **N1=55/N2=104**: **157 auto-identical**, **2 new N1 findings**, both in the newly added full graphics-source coverage:

- `u13-m1-compat-shim.cpp:415`, `resolve_oh_wm_funcs`: bridge `RTLD_NOW|RTLD_NOLOAD`.
- `u13-m1-compat-shim.cpp:1408`, `eglCreateWindowSurface`: EGL `RTLD_NOW|RTLD_NOLOAD`.

`new-n1-lineage.json` proves those exact statements also exist in the baseline N2 source at415/1327. This does not prove resident handle availability; both remain explicit outer review. The default native gate is **REJECT**. `auto_approve_exceptions` is actually run **without --apply**, exits3 and prints157 identical/2 new. `registry-delta.json` proposes157 rows with real, landing-listed evidence paths; `outer-review.json` lists2 new. A separate local proposed-registry replay remains REJECT on those2; no master registry was changed. The new-native admission draft is empty because all changed paths already exist in U12.

## Actual production dry-runs

Mac actual OS **Darwin/arm64**: required DEX/LLVM tools exercised, actual DEX read0, RB0, T4b0, frozen0, composed frozen violations0 on each of319-path/321-assertion board identity sets. **Production dry-run exits2 at the exact static gate above**, before image/native production gates. No board/device access occurs.

Supplemental image check: G1 PASS; G2 false with empty candidate/reference disassembly. A separate read-only SSH probe exits255, `Operation not permitted`, so the G2 observation is **not proof of a suspend-check regression**; all27 selected images and effective JARs remain identical to U12. Original SSH log is private persistent evidence; public copy redacts server identity only and retains its original SHA.

VM status **unknown**. The initial7s probe and outer-requested **60s `orb -m a2hlab uname -m` retry** have no response; retry exits124. No VM production command reached, and no historical U12 PASS was borrowed. Outer explicitly permits this honest unknown pending cx-t0's pre-window fresh VM run. Exact command, from a Mac environment with the actual shared `WORKSPACES`, `MAC_HOME` and `LAB_HOME` already set:

After outer reported the23:05 VM restart, a fresh60s **read-only** `uname -m; cat /proc/uptime` probe also timed out124. No build was active on that VM for this task; the three donor artifacts, runtime69-object sets and completed donor tee logs were independently checked on Mac. Per the new resource rule, this lane does not start a full VM gate run; the command below is a handoff to cx-t0, not an action performed after that instruction.

```bash
orb -m a2hlab env WORKSPACES="$WORKSPACES" MAC_HOME="$MAC_HOME" LAB_HOME="$LAB_HOME" \
  bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-u13-assembly-draft/vm-dry-run.sh"
```

The script asserts actual Linux and both exact manifest hashes, selects the existing VM DEX/LLVM proxies, and runtime-tees output. Its production command is the same master `u7_executor.py --dry-run --package <exact persistent draft> --baseline-native <exact U12 native> --oatdump <trusted oatdump_remote.sh>`, never an executor activation. As currently unadmitted it should refuse, not pass. After outer review/rebinding, both surfaces must be rerun against the newly frozen bundle SHA; this draft contains no permission to enable execution.

Board reference fingerprints are5ea/5cd RUNTIME `0bbf21f3066c`,61b `8e54cff4ce4f`, BOOTIMAGE `ee927db88a67` (composition only, not live measurements). `rollback.json` identifies exact U12 baseline bytes and paired aliases; actual window recovery-to-unified-state remains cx-t0/outer policy, not performed here.

## Provenance and verification

`donor-provenance.json` and `provenance-index.json` separate U13 donor receipts from inherited U12 receipts. Runtime control exactly reproduces ac59, two U13 builds reproduce18763,69 objects with only graphics/asset-manager changed. VLC and policy likewise have two identical builds and exact base reproductions. These are **reviewed donor facts**, not new builds by this assembler. Seventeen source/receipt/recipe snapshots and three runtime-tee log hashes are retained; unchanged artifacts keep the original U12 paired bake receipt. `$REPO` in public source references denotes the producing worktree; persistent artifact references explicitly use `$WORKSPACES/westlake-harness-bms`, not the landed master directory.

Tests validate disabled authorization, held host, paired aliases, boundary-safe worktree normalization, complete static inventory and honest dry-run results without requiring `.artifacts`. Python/Rust/contracts, portable no-artifact checkout replay and landing preflight outputs are delivered under `evidence/`. This is an offline **reviewable draft**, not an admitted window or a screenshot result. VLC still has conditional owner-scope dependency; no automatic first-fatal or lighting gain is attributed to added exports alone.
