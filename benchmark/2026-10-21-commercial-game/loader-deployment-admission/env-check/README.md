# G19 U7 execution-environment addendum

**The reviewed original U7 CLI is not executable end-to-end as-is.** This is a newly reproduced constructor/start integration defect, not an old-owned-state requirement. Main was exactly `6f69b99df7fbbde75c9c438f534cc2d4121a3752` at capture. No deployment, device probe, build, SSH, HDC retry, wrapper, permission change or G20 modification was performed.

## Blocking original call path

`u7_executor.py:380–389` constructs `DeviceIO` without calling `Deployment.__init__` and sets only `b`, `board`, `boot`, `out`, and `serial`. Its inherited `deploy_generation.py:254–257` start method immediately reads `self.a.no_label_recipe`, then requires `self.m` for the label recipe. Both fields are missing. There is no `--no-label-recipe` option on the original U7 CLI to change that fact, and this review adds none.

`python3 replay_start_binding.py` compiles the exact pinned constructor/start AST bodies, substitutes only inert platform/import/Board dependencies, constructs the object, and calls its inherited start. **rc=0 means the counterexample was reproduced**, not successful service start: `AttributeError: 'DeviceIO' object has no attribute 'a'`. No service command is reached. The script checks that both `a` and `m` are absent; it does not monkeypatch those inputs or propose a runtime workaround.

U7 apply calls this start after binding/verifying the candidate (`u7_executor.py:326`). Its automatic rollback also calls it after restoring/verifying baseline layers (`:363`). The second failure can end in `recovery_required`, with the parent stopped (`:368–374`). Thus native gate approval alone cannot make this version safe to execute. The minimal next change belongs to the deployment-tool owner: bind the inherited start inputs correctly for both candidate activation and baseline restoration, retaining the label recipe, then independently replay both paths. **This card does not edit that tool or create a startup wrapper.** The earlier G19 transaction-architecture conclusion remains valid; an end-to-end executability inference is superseded by this finding.

Pinned originals: U7 `53dcbc9b7cb6bdf41e54d11d5fff4d0992d33dedda6fed25701135fad3c164c0`; deploy_generation `0a68e23c4420a521c8548918323c40d806de0751c4a9883d14ab7f4e994d916a`. Original and archived source pins are in `source-pins.json`. Line references throughout this document address those archived originals.

## Actual environment observations

| Read-only command/observation | Result | Limit |
|---|---|---|
| `orb -m a2hlab sh -c 'uname -s; command -v python3; command -v mac; command -v bash'` | No output before 15 s capture timeout | Local capture rc124; original OrbStack exit status unavailable. No retry, VM restart or fallback attempted. |
| Original `westlake-inputs/tools/board_note.sh held 5ea34a4500000000000000001123012c` | rc1, empty stdout/stderr | No live lane holder reported at sample. No lock acquisition/unlock. |
| Original `python3 scripts/lab/lab_paths.py` | rc0, workspace parent resolved | Local Mac resolution only; VM view remains unverified. No environment dump. |
| Original `python3 scripts/lab/u7_executor.py --help` | rc0; four original modes present | Help does not create DeviceIO or test apply. |
| Both assembly-02 bundles/native manifests | Present, hashes in `path-inventory.json` | Location check; not a fresh native approval. |

`commands.json` retains argv, timestamps, rc and stdout/stderr SHA256. For a timeout, the locally assigned rc is explicitly distinguished from a process exit code. Public transcripts normalize local workspace/home prefixes; original stream hashes are retained.

The original execution chain is `orb -m a2hlab` → Linux Python U7 → `lab_paths` → existing `westlake-inputs/tools/hdc_mac.sh` → OrbStack `mac` → Mac HDC. U7 explicitly rejects Darwin DeviceIO (`:381`). The HDC helper maps local file operands and forwards encoded argv; it may create local cache directories, so it was inspected rather than invoked here. Mac HDC exists at `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`. Both helper scripts exist and are executable. `lab_paths.py:26–49` resolves WORKSPACES from its configured input or directory markers, then selects `westlake-inputs/tools` and the main harness; do not guess a VM-only alternate tree.

U7 constructs Board with `mac <tools>/board_note.sh` (`:386–388`). Board `ready()` (`bms_batch.py:441–464`) requires the exact lane holder, attached serial and stable boot before commands. No global permissive or identity bypass is part of this review. VM `mac`, shared assembly paths and the VM's remote-oatdump prerequisites were not established because the single VM probe timed out; they are precise outstanding environment checks, not claims of missing installed files.

Two locks are separate: the persistent lane board lock managed by `board_note.sh` and the U7 process flock at `$WORKSPACES/westlake-generation-state/5ea34a4500000000000000001123012c/u7-executor.lock` (`u7_executor.py:548–551`). The latter exists as a zero-byte file; existence/size does not prove that its flock is free. It was neither opened for locking nor truncated. The default board holder file was absent, consistent with held rc1. Do not acquire a second lane or assume an empty holder is authorization.

## G20 inputs and unchanged gate entry

The landed G20 README and next-command records were read from main `6f69b99df7`. Actual private assembly root:

`$WORKSPACES/westlake-harness-g10-env/benchmark/2026-10-21-commercial-game/gles-transaction-package/.private/assembly-02`

| Member | SHA256 at read |
|---|---|
| `baseline/bundle.json` | `737da76e29a72f533ab9de7eb345b80fb06a75e795a0b8efc8f55ab886bd1067` |
| `candidate/bundle.json` | `4f73176b12837c6301a3e6e664bffdc8d3d5ee9278f2b499c6e95445d0e54524` |
| `baseline/native/package.json` | `00c5145936abe50d0cfc557712bbe34af966d7efc5e5f95cd45efbd92f82449e` |
| `candidate/native/package.json` | `ef85106919f294656d50db7ff94df071d55123437161d71d0646136e2e10ae23` |

G20 records 319/319 baseline hashes, two logical loader differences and **32 planned writes including 30 same-SHA boot/JAR members**. These are G20 evidence, not a reassembly or independent full-binary rehash here. Native exceptions are under actual outer review. The existing `run_gates.py --only u7 --oatdump <main>/scripts/lab/oatdump_remote.sh --lab-home-from-provenance` is the next original gate driver after signing, exactly as `sources/.../gles-transaction-package/next-commands.json` records. No gate is rerun by this card.

`oatdump_remote.sh:20–25` requires LAB_HOME; its default remote target is hw248 and it uses ssh/scp/shasum. The actual value must be derived using the existing G20 `run_gates.py` regex from `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt`. Do not guess it, substitute a server path, or assume a Mac export survives into OrbStack. Original U7 apply reruns preflight, so the Linux process itself also needs the verified oatdump path and provenance-derived LAB_HOME. A prior Mac dry-run does not skip this requirement.

## Stop/start applicability and current parent

The latest consumed G19 process evidence contains root `appspawn-x` PID 6274, PPID 1 on boot `a1d869b4-69a2-40a4-937e-4860f5b54239`. It is an archived observation, not a new current-process measurement. Historical U13 recover cfg/script preserve init's ondemand appspawn-x service; they do not directly exec a replacement daemon. This supports investigating the existing `begetctl` entry but PID/PPID/name alone cannot prove current service ownership or parent birth. No fresh parent environ was read.

Original `Deployment.stop()` (`:242–253`) cold-stops HelloWorld, Zigzag and Wikipedia using the existing BMS/UID path, refuses other observed non-root appspawn-x children, then issues `begetctl stop_service appspawn-x` and waits for all matching processes to disappear. It does not promise to stop a live commercial-game child. The outer window must establish that child quiescence and service ownership before proceeding; no generic kill or restart of a live child is authorized here.

Original `Deployment.start()` (`:254–267`) would run the label recipe, issue `begetctl start_service appspawn-x`, verify one root parent and its executable SHA, and set/check AppSpawnX socket owner/mode/label. These are real writes included in the original entry, not a read-only start or only two loader binds. Their inputs are precisely where the reproduced constructor defect intervenes. U7 verify (`:484–513`) launches a HelloWorld control child and checks its view/maps; this is not commercial-game acceptance. Rollback's special OrganicMaps cleanup is ownership-bounded (`:397–430`), not an arbitrary-game cleanup facility.

## Shortest bounded window and restoration checklist — blocked template

**Do not execute the write steps with the currently pinned defective tool.** This is a reviewable checklist for outer after a corrected tool is reviewed, native signing/full preflight passes, and environment/service checks are complete. Variables denote explicit outer-selected paths/lane; they are not guessed hidden values. No executable wrapper is supplied.

1. Before opening the window, verify VM/Linux Python/mac and shared assembly visibility, the original HDC/board_note path, and remote oatdump provenance in that same execution environment. Reuse the original gate driver above; retain argv/stdout/stderr/rc and exact final tool/package/policy pins. If any fails, stop before lock/apply.
2. Outer takes or verifies its existing board lock for full serial `5ea34a4500000000000000001123012c`, records lane, fresh boot, parent PID/birth/exe and actual init service, absence of live test children, original power values, deadline and signed recovery inputs. Keep original mount stacks/Boat overlays. Original lock commands are `board_note.sh lock <absolute-board> <serial> <lane> <reason>` and `held <serial>`; this card executes neither lock nor unlock. Do not forge an old owned-state record.
3. From a2hlab, use the original mode, with a new journal and distinct reports, persistent stdout/stderr plus rc captured by outer:

```sh
python3 "$MAIN/scripts/lab/u7_executor.py" --apply \
  --package "$ASSEMBLY/candidate" --baseline-native "$ASSEMBLY/baseline/native" \
  --oatdump "$MAIN/scripts/lab/oatdump_remote.sh" \
  --serial 5ea34a4500000000000000001123012c --lane "$LANE" \
  --journal "$WINDOW/journal.json" --out "$WINDOW/apply.json"
```

`$MAIN` is the verified main checkout; `$ASSEMBLY` is the exact assembly-02 directory above; `$WINDOW` is a new persistent outer evidence directory. The original executor acquires its own process flock and creates a genuine journal only after baseline/boot/mount checks. LAB_HOME must already be bound from verified provenance in this process. Never run the present template to “test” the known start defect.

4. The total window is <=30 minutes. Begin restoration by minute 20, earlier on apply/verification failure. U7 automatically attempts rollback after apply failure; inspect the journal rather than replacing it or assuming the exception means no changes. Keep the board lane lock while recovery is unresolved.
5. Same-boot restoration uses the **same real journal**, no replacement baseline or synthetic state:

```sh
python3 "$MAIN/scripts/lab/u7_executor.py" --rollback \
  --serial 5ea34a4500000000000000001123012c --lane "$LANE" \
  --journal "$WINDOW/journal.json" --out "$WINDOW/rollback.json"
```

Original rollback rechecks its baseline gate/frozen binding, stops through the original guard, removes only its owned layers in reverse order, verifies original complete mount stacks and baseline hashes, then starts/verifies baseline. Wrong boot or ownership stops it; `--restore-baseline` is a separate original cross-boot mode requiring `--from-journal`, a new journal and additional evidence, not an automatic fallback. A startup defect/recovery_required status keeps the lane lock and requires outer resolution; do not bypass the label recipe or synthesize missing attributes in a launcher.
6. After verified baseline restoration, outer checks both loader aliases b8be, original boot/JAR and all preserved Boat identities, baseline service/parent and original power values; retain signed recovery evidence, then release via the original `board_note.sh unlock <absolute-board> <serial> <same-lane>`. This executor does not enforce the 20/30-minute deadline or restore arbitrary power settings for outer.

## Handoff

`results.json` is the machine-readable verdict. `start-binding-replay.stdout.txt` is the exact reproducible counterexample. `landing-paths.txt` contains this new subdirectory only; previous G19/T37/T38 packages and pins are unchanged. No shared Git commit/push or direct bus message was attempted. Outer should relay this blocker before any apply; current assembly/native review can continue independently.
