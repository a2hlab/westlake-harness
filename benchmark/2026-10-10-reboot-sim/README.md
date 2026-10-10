# Minimal advisory reboot simulator

## Evidence and rejected shortcut

Bind mounts do not survive a real reboot. A currently correct mounted inode or
running PID is **not** evidence that the hidden physical `/system` file has the
same bytes or label. The simulator therefore never fills its physical inventory
from `snapshot.labels` or silently borrows an earlier successful run.

The 16 known-answer tests are entirely synthetic: entrypoint denial, mapped
`data_local_tmp` libraries, a seccomp/cfg visible count of zero, complete replay,
missing evidence, stale identity, late recovery, and multiple visible filters.
The Rust `demo_baseline_reboot_sim` selector invokes those tests. These are wall
**classes**, not a claim that the actual 61b seccomp cause was a missing file or
wrong factory label. Direct 61b/5ea captures show factory `system_lib_file` for
seccomp; changing labels did not fix the actual sandbox lookup.

No board, HDC, VM or SSH operation was executed. Real 61b prediction remains
pending physical-underlay/closure/query inputs. This is additional evidence for
the sealing process, not a new hard prerequisite or authorization to reboot.

## Invocation and input identity

```sh
python3 scripts/lab/reboot_sim.py --inputs "$PINNED_INPUTS_JSON" \
  --out "$NEW_PREDICTION_DIR"
```

The inputs manifest has `schema_version: 1` and exactly eight entries in
`inputs`: `plan`, `snapshot`, `inventory`, `autostart`, `closure`, `recipe`,
`queries`, `policy`. Each entry is `{path, sha256}`; relative paths are relative
to that manifest, and environment variables are expanded. Every input is read
and hashed before any prediction is written. Missing/drifted data exits 2 with
`NO_PREDICTION` and creates no output. The snapshot and inventory are mutually
bound; policy/recipe query bindings must match the actual input bytes.

For real `board_state_snapshot.py` output, add `raw_inputs`: each item name pins
its stdout file; `<name>.stderr` pins its stderr file. Pins must equal the
snapshot's own receipt hashes. Failed mandatory reads, missing raw pins, an
incomplete snapshot, changed boot, or a different captured plan refuse to
predict. Optional diagnostic probes remain data, not proof of visibility.

Output is deterministic `prediction.json` plus `prediction.tsv`. Return 0 is a
conditional advisory PASS, 1 is a FAIL/UNKNOWN table, and 2 is input refusal.
`execution_enabled=false`, `board_access=false`, `advisory_only=true` are always
present. No timestamp is injected into the prediction, so identical inputs
produce byte-identical JSON/TSV in two independent output directories.

## Input normalization contract

- `plan`: the deployment `mounts` or recovery `recover_layers` list with target,
  source and file/directory kind. Relative package sources need an explicit
  persistent `/data` `autostart.source_root`; no archive location is guessed.
- `snapshot`: the newly landed snapshot JSON, including complete/boot_stable,
  serial, boot ID and config-policy parameter observations. Explicit `null` for
  `const.cust.config_dir_layer` means **proved unset** and permits the documented
  `/system:/chipset:/sys_prod:/chip_prod` fallback. A missing key or unparsed
  error string remains UNKNOWN; the normalizer must not convert query failure
  into unset.
- `inventory`: `snapshot_sha256`, `physical_files`, `source_files`, plus explicit
  `physical_complete`/`source_complete`. Each inode row has `kind`, `label`,
  `evidence`, and file `sha256`. Source paths are persistent `/data` paths.
  Missing physical data is UNKNOWN unless inventory completeness proves absence.
  The current mounted snapshot does not supply a bind-hidden physical underlay.
- `autostart`: serial, explicit `enabled` and `apply_label_recipe`,
  `recover_phase` (`before-services` is the supported replay order), init
  `services` with `path`, `secon`, evidence, and `seccomp` with filter name,
  child domain and evidence. This is a pinned normalization of actual cfg and
  recovery scripts, not inferred init timing. Late/unknown timing cannot PASS.
  Optional `preloaded_files` rows carry `path`, `domain`, `phase: server-start`
  and `evidence`. The mandatory `/system/etc/sandbox/appdata-sandbox.json` read
  in appspawn cannot be omitted by supplying an empty list. These files must
  permit read/open/getattr and directory traversal **before daemon preload**;
  fixing labels after that stage cannot repair the cached configuration.
- `closure`: explicit `roots` with path/domain and `objects` keyed by canonical
  ELF target. Each object binds its SHA and `needed` list to predicted bytes;
  each edge states soname, namespace, resolved_path and resolution evidence.
  An unresolved edge fails, missing closure/SHA evidence is UNKNOWN. It does not
  invent linker inheritance or resolve a SONAME by finding any same-name file.
- `recipe`: the one canonical `knowledge/gates/selinux-label-recipe.json`.
  Ordered match/context rules are reused directly through the shared helper.
- `queries`: exact domain/type/class/permission answers, including explicit
  denies, policy SHA, raw recipe SHA and query-provider/tool SHA. Missing answers
  are UNKNOWN, never an implicit deny or permit.

## Policy query adapter

`collect_queries(run_query, policy, recipe_path, inventory, autostart, closure,
query_tool)` accepts an explicit callable with signature
`run_query(policy, domain, label, permission, class)`.
It records returned allow rows or an explicit no-allow response and hashes the
policy, unique recipe and provider source. Domain/type combinations come from
the inputs and the recipe; it does not require a second `recipe.entries` label
table. The exporter is tested with a mock callable; actual remote `sesearch`
export is for the accessible outer lane, not executed here.
The landed `sepolicy_gate.py` currently performs queries inside its CLI and
does not expose a public `run_query` function. The earlier direct-import
example was incorrect; supply a real adapter, preserving tool failures versus
successful empty results. Missing positive-proof rows are not denial evidence.

Example outer-side export after all inputs have been normalized and pinned:

```python
import json
from pathlib import Path
from reboot_sim import collect_queries

answers = collect_queries(
    run_query, policy_path, recipe_path,
    json.loads(inventory_path.read_text()),
    json.loads(autostart_path.read_text()),
    json.loads(closure_path.read_text()), query_tool_path)
queries_path.write_text(json.dumps(answers, indent=2) + "\n")
```

Pin the resulting file into `inputs.queries`; never reuse the old fixture-recipe
proof as evidence for a changed recipe. The actual query interface is
responsible for policy semantics/conditional allow evaluation; unavailable
tools must raise, not return an empty list that would masquerade as a deny.

## Three checks and limits

The server-start preload check is now mandatory in addition to the original
three classes: sandbox configuration read/open/getattr and its directory
traversal must succeed before the daemon caches it. Optional extra configs
share that rule and require explicit source/phase metadata. See
`server-preload/` for the new tests and the separately pending real-input proof.

1. Every supplied init service uses its cfg `secon` domain; entrypoint/execute
   and directory traversal are queried for the predicted inode context.
2. Host/critical native roots and their pinned DT_NEEDED edges must exist and
   allow read/open/map in the supplied domain. Directory traversal and ELF
   identity are checked. Full namespace/loader reconstruction is out of scope.
3. Exactly one filter is visible across the documented/configured cfg layers.
   A physically present file denied by directory search or file getattr is not
   counted. Unknown inventory or missing policy proof prevents a PASS.

Current binds are discarded. Proved physical files persist; enabled,
before-service recovery replays persistent source trees in plan order.
Applying the unique recipe is a **conditional assumption** that its generated
shell succeeds and readback passes. Relabel permission, capabilities, actual
init scheduling and app rendering are not simulated. An old in-memory INVALID
latch clears on a real reboot; this does not imply a new exec attempt succeeds.

The delete-only seccomp revision leaves the directory's generic default
`system_file`; the explicitly tested factory mismatch is documented in
`benchmark/2026-10-10-selinux-stock-correction/`. This simulator neither adds a
second label override nor presents that fallback as a verified live fix.

## Current verification status

Python/Rust known answers and user-path/compile checks are fresh. Formal
`agent-spec contract`/`lifecycle` currently refuse the inherited master project
spec's new unrecognized top-level section at line 16. The original refusal is
in `evidence/contract-refusal.txt` and `evidence/lifecycle-refusal.txt`; no spec
was edited to obtain a PASS. The outer has been asked to put that section under
a legal Constraints/Decisions heading, after which lifecycle must be rerun.
Live snapshot normalization and fresh query export remain pending; tests are
not historical 61b board evidence.
