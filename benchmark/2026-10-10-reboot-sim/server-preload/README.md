# Server-start preload rule and real-input audit

## Evidence first

The original three-check simulator could pass native mapping and filter checks
while omitting the configuration read that happens **once at daemon startup**.
The outer accepted the 2026-10-10 seccomp cause: pre-fix 61b had
`appdata-sandbox.json=data_local_tmp`; a newly started daemon after the recipe
repair no longer hit the filter-name failure. Checking only child-time filters
misses this earlier dependency.

The frozen reference source registers `PreLoadAppSandboxCfg` at
`STAGE_SERVER_PRELOAD`; `StartSpawnService` executes that stage before serving
children. Its sandbox loader reuses already-created manager data rather than
reloading it on every spawn. Source paths, SHA256 and exact lines are in
`evidence/live-input-audit.json`. These are reference-source explanations, not
a new claim that this frozen source byte-reproduces the deployed host.

## Implemented rule

- `/system/etc/sandbox/appdata-sandbox.json` in the appspawn domain is always
  checked, even when `preloaded_files` is absent or empty.
- Predicted directory traversal and file read/open/getattr must pass.
  Each row names `phase=server-start`, cache semantics and rule provenance.
- Optional extra preload files require canonical paths, explicit domains,
  `phase=server-start` and evidence; duplicates and malformed rows refuse.
- Recovery/relabel before services may repair the predicted inode. An
  after-services repair cannot substitute for the earlier preload state.
- The query exporter includes preload domains. The landed sepolicy CLI does
  not expose the `run_query` API claimed by the earlier README; the corrected
  example requires a real explicit adapter. Missing allow rows in the 32-proof
  positive-only report are **not** automatically interpreted as denials.

The suite now has **20 synthetic tests**, including the four new preload
cases; it still does not turn synthetic scaffolding into a real board answer.
The earlier 16-test receipts remain historical and unchanged.

## Actual known-answer inputs: partial, not safe

cc-t3 supplied the persistent `$HOME/a2hlab-provision/t2e-inputs/` directory.
Its two real JSON captures have all original raw hashes verified, but the 61b
one is **post-label-fix**, not the negative capture: both JSONs already have
the sandbox file labeled `system_etc_file`. Neither carries a complete plan.
Pre-fix evidence is the separately pinned manual `61b.txt` and 24-row
`61b-mislabeled.txt` (23 libraries plus the sandbox JSON).

The 23 library rows contain basenames only. Their full route-a paths and
healthy per-file labels are not in the supplied tool captures. Earlier
first-board fixtures normalized them to root paths as a replay assumption;
that assumption must **not** be promoted to real object identities here.
The negative library list is preserved as source evidence, not guessed paths.

Canonical library paths/labels, explicit DATA-type policy query outputs,
underlying physical/source inventories, and namespace-bound DT_NEEDED closure
have been requested on the board. Until these are supplied, the full real
61b/5cd prediction and any global `safe_to_reboot` verdict remain pending.
Healthy observed labels or successful live reboot smoke do not fill those
missing input records. No snapshot bytes or facts are altered to force a PASS.

## Before the final reboot

After the accessible lane completes and pins the real eight-input manifest,
run the unchanged file-only interface:

```sh
python3 scripts/lab/reboot_sim.py --inputs "$PINNED_INPUTS_JSON" \
  --out "$FRESH_PRE_REBOOT_PREDICTION_DIR"
```

There is no execution switch or board transport in this command. Missing or
drifted inputs refuse prediction; unresolved checks cannot become PASS. A
conditional advisory PASS still does not authorize the reboot or replace
the actual post-reboot 128-app signoff.

## Fresh validation

`evidence/` contains raw Python, Rust and user-path outputs. Formal lifecycle
still refuses the inherited project's unrecognized top-level heading at line
16; its original refusal is retained and no spec was edited for acceptance.
This landing is the rule/tool correction only, not completion of the real
negative and positive known-answer requirement. Zero HDC, SSH, VM, lock or
board action was attempted; git metadata is read-only, so outer landing is
required.
