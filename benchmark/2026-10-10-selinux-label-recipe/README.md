# One SELinux label recipe for deployment and boot recovery

## Evidence and corrected assumption

The previous generic `system_file` relabel did not provide the init entry's
`appspawn_exec` label. Binding files from `/data` also preserved `data_local_tmp`
or `data_file`, which the appspawn domain cannot map. These are independent of
file SHA identity. The current 61b recovery subsequently failed a seccomp layer
lookup; this delivery does **not** claim that labels alone light an app.

This is an offline tool change: no HDC, board, VM, SSH, mount, lock, reboot or
security-policy operation was executed. The independent fixture covers the
exec/library walls and the stock seccomp-label exception. The 18 Python tests
pass; the Rust selector runs the same 18 tests. The six existing current-master
deployer frozen-policy tests also pass against the patched deployer.

## Single source and provenance

`knowledge/gates/selinux-label-recipe.json` is the only label policy. Ordered
`rules[].match` (`exact`, `prefix`, `glob`) and `context`, `default.context`,
`required_targets`, and `sources` are directly readable by the reboot simulator
and sepolicy checker. There is no second hand-maintained shell label table.

The PR03 source SHA is
`7eaf26fbbaf69227fcde865bd259fb3a4f8ffae9cd5aab00b4a6c2302ac5b4ab`
(lines 153–174, including 158–161). The frozen cc-wiki recover v2 is commit
`1483c626b8`, script SHA
`b9063f5c67386f2f3f897be9804ba22f6f33c43b8cfd98d6947b11a588aa990d`.
Paths and line ranges are recorded in the JSON; the small extracts are in
`evidence/source-excerpts.txt`. The seccomp override preserves the stock
`/system/lib64/seccomp` directory/filter-file `system_file` labels reported by
cc-t3's read-only 5ea comparison in its board entry at 10:30:56 on 2026-10-10.
It precedes the generic library suffix rule and does not disable seccomp.

`scripts/lab/selinux_label_recipe.sh` is generated from that JSON. Its embedded
hash is the canonical sorted JSON hash, not the raw file hash. Tests reject a
stale generated script. Python deployment generates these same script bytes at
runtime, archives them with the raw JSON SHA, and invokes that script through
its existing lock/boot-guarded shell. A second independent Python readback must
also pass before `begetctl start_service`.

## Invocation

Read-only Mac audit (the full OH serial must be whitelisted):

```sh
python3 scripts/lab/selinux_label_audit.py "$SERIAL" "$DEPLOY_PLAN" \
  --hdc "$HDC" --out "$NEW_EVIDENCE_DIR"
```

The plan is a native package `mounts`/`files` object or a `recover_layers`
object; a targets-only list is also supported. Each target needs an explicit
`file`/`directory` kind or a kind provable from package files. A transaction
journal's changed-files-only list is not a full deployment plan. The required
coverage is mandatory. Arbitrary shell paths, duplicates, absent files,
unreadable labels, partial collection or a changed boot all fail closed.

Each recursive read is archived with command, stdout, stderr and exit status.
Every mismatch prints the path, expected context and actual context. Audit is
read-only. Target count comes from the supplied plan (including 56-layer plans),
not a hardcoded assumption that every generation contains exactly 56 layers.

Generate the board script on Mac, then archive/upload it with its JSON and SHAs:

```sh
python3 scripts/lab/selinux_label_audit.py generate-sh --out label-recipe.sh
sh label-recipe.sh audit label-plan.tsv
sh label-recipe.sh apply label-plan.tsv
sh label-recipe.sh apply-source label-plan.tsv
sh label-recipe.sh context /system/bin/appspawn-x
```

Only the last command and `audit` modes are read-only. `apply` modes require the
caller's deployment authorization. The generated script uses POSIX sh builtins
and toybox applets only, checks all plan rows before relabeling, uses `chcon -h`
without following symlinks, reads every label back and prints path/mismatch
counts. A failed or non-sticking relabel exits nonzero. No Python/jq is required
on the board.

TSV rows are `kind<TAB>canonical-target[<TAB>archived-source]`. The source is
mandatory for `*-source` modes and must be under `/data`. The third column is
ignored by target modes. The shell counts path occurrences when scopes overlap;
the Python audit deduplicates paths. Their verdicts, not overlapping counts,
are identical on the same independent fixture.

## cc-wiki recover integration

This delivery does not edit the other lane's recover script. Its installer
should ship the generated script and record both recipe/script SHAs; replace
the old `ctx_for` and duplicated chcon/readback blocks with calls to this file.
For the existing six-column recovery table:

```sh
awk -F '\t' 'NF == 6 { print $2 "\t" $4 "\t" $5 }' \
  "$ROOT/u13-recover-table.tsv" > "$ROOT/label-plan.tsv"
sh "$ROOT/selinux_label_recipe.sh" apply-source "$ROOT/label-plan.tsv" \
  >> "$LOG" 2>&1 || fail LABEL_SOURCE_RECIPE
```

Run the source call after verifying all archived-source SHAs and before binds;
keep the existing ordered binds, WAL, byte checks and permission settings.
After all binds, run `apply` then `audit` on the same table before starting the
service. Do not append a separate hardcoded library-tree relabel afterwards.
This preserves fonts, private app labels and the stock seccomp exception.
The two mocked caller paths repair to the same expected contexts. Real boot
integration and sepolicy proof remain outer-reviewed follow-up work.

## Deployment integration and rollback

`deploy_generation.py` is based on the current master deployer SHA
`59ac3fd48bf58674fb428a6fc21dc36e4e2f454e126876114d088bdbbb7e159c`.
The narrow `deploy_generation.patch` adds default pre-start repair/readback,
`--no-label-recipe`, and Mac→VM flag forwarding. Parent/socket validation,
native/frozen gates, transaction and rollback code are unchanged. Explicit
opt-out skips only this new gate and is not a policy bypass. Default startup
refuses if the JSON/helper is absent; package/tool closures must include them.

To revert the code change, reverse the supplied patch and stop shipping the
new helper; do not use code rollback as authorization to change board labels.
Existing deployer tests run using the report's reproducible `run_regression.py`
overlay: patched deployer, current-master modules/frozen registry, mock-only
test transport. No historical PASS is substituted for fresh tests.

## Reproduction

```sh
python3 scripts/lab/test_selinux_label_audit.py -v
cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test selinux_label_recipe -- --nocapture
python3 benchmark/2026-10-10-selinux-label-recipe/run_regression.py \
  --master "$WORKSPACES/westlake-harness" --out "$NEW_REGRESSION_DIR"
```

Fresh command statuses, generated-script identity and source hashes are in
`results.json`; raw local test outputs are in `evidence/`. Actual app lighting,
init INVALID recovery, SELinux allow-rule changes and seccomp visibility are
not proven by these fixtures.
