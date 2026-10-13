# F28 Boat provider and exact expected union

The old r2 provider required runtime947. This sibling replaces only that artifact with f28 and regenerates its table/worker pins; the original provider, installer, CAS/partial rollback, eleven placements, seven binds and RouteB488 checks remain. Reference recover/cfg bytes remain unchanged. Stock187 is still required before application. Existing freezes and signed V1 remain intact.

The actual5cd example uses outer/final-v2-5cd-postarchive-readonly/capture.json: complete497 + exact319, Boat UID20011301, boot362f2212-1a42-4c1a-8487-0dddb091c74b, root absent. It is disabled and unsigned. Source/expected union is954 (original940 plus13 files and BoatAPK), including all three private Boat targets. Compiler outputs expected identity, never observed acceptance.

After exact landing, regenerate from main; producer paths in this example are historical evidence, not main execution inputs:

```sh
export WORKSPACES=/path/to/workspaces
P=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-f28
C=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-postarchive-readonly/capture.json
OUT=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-f28-main
python3 "$P/board5cd/provider/prepare.py" --capture "$C" --out "$OUT"
python3 "$P/selfcheck/bind_request.py" --template "$P/selfcheck/request.5cd.pending.json" --plan "$OUT/plan.disabled.json" --out "$OUT/request.json"
python3 "$P/selfcheck/compile_selfcheck.py" --request "$OUT/request.json" --out "$OUT/composed"
```

`provider.json` is the existing typed provider row; wrap it in `demo-restore-deployment/v1` with execution_enabled=false. Standard argv remains `boat_provider.py --seal composed/seal-candidate.json --serial SERIAL --deployment deployment.disabled.json --out NEW`. Independent program/common/executor/plan pins and a fresh outer authorization are still required for actual execution. Main-bound execution must never use the producer example.

`board5cd/entry/restore_entry.py --v2-recipe RECIPE --recipe-sha256 SHA --out NEW` previews only. The complete route requires route_b.mode=restore-directory-complete and original487 transaction/placement receipts plus directory completion. verify-existing is preservation only. A current362f complete-recovery rebase is a separate successor under development: original T6 hard-pins the43bc binding, and its executor requires absent creation directories. This package does not claim that old43bc admission can restore current362f, and does not provide fake authorization. No device call, reboot, privacy acceptance or seal signing is performed.

61b remains disabled and protected. T0 consumes composed/planned_selfcheck.json/all_expected_sha256 and its full SHA for the single954 identity; do not use fiveea's RouteB absence. Dynamic WL_PARENT_ID remains restricted to the original independently observed sameboot WMS/host mechanism.

Offline results: provider11+11, entry5+6, preinstall6+6, union7, exact-source delta4, request binding3 =59 tests PASS. Actual497 capture compiled through the original provider validation and954 composition; standard disabled argv rc0. Original940 observation is a negative input and cannot pass954. These are not live candidate acceptance.
