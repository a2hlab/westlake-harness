# 5cd receipt review and disabled 61b preparation

The 5cd stage is backed by actual placement and live receipts, not only an expected954 inventory. Offline review found stage rc0, eleven placements,496 preserved objects, complete62-target preboot snapshot, successful policy gate, one boot to c9436daa-b3ca-44dc-985f-9ee03445567a, READY56/BOUND7, two954/954 live selfchecks, and34/34 smoke checks. Runtime9745004d10ce / boot-image ee927db88a67 match the archived algorithm and actual smoke. `results.json` pins every reviewed source. `facts.txt` is copied byte-for-byte from the actual control run. Outer reports reviewing t20 images; this review does not claim another visual review.

At review time `ready-to-unlock.json` still says final-host visual pending, and no actual unlock receipt is present in the stage top-level. Boat playability on5cd is recorded not_tested. This does not request another full128 on5cd, nor turn these receipts into final candidate signoff. Existing5ea game/full128 acceptance must be bound by the final signatory.61b remains protected pending explicit user unseal authorization.

## Existing offline commands

Run from main after exact landing. These commands do not execute device transport. Use a fresh output directory. Never execute the producer's historical example request on the board.

```sh
cd "$WORKSPACES/westlake-harness"
B=benchmark/2026-10-09-demo-boatattack/v2-20261013
P="$B/integration/final-v2-f28"
OUT="$B/outer/final-v2-61b-disabled-next"
APK="$WORKSPACES/westlake-bms-suite/APKS/BoatAttack/dist/boat-attack-a.apk"
PRE="$B/outer/61b-v2-readonly-preinstall/capture.json"
python3 "$P/board61b/entry/prepare_request.py" \
  --capture "$PRE" --apk "$APK" --out "$OUT/preinstall"
REQUEST_SHA=$(shasum -a 256 "$OUT/preinstall/request.disabled.json" | cut -d ' ' -f 1)
python3 "$P/board61b/entry/prepare_boat.py" \
  --request "$OUT/preinstall/request.disabled.json" \
  --request-sha256 "$REQUEST_SHA" --out "$OUT/preview-not-created"
python3 "$P/board61b/provider/prepare.py" --out "$OUT/blueprint.disabled.json"
```

Original APK SHA is8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444. This exact compiler/preview was run locally with rc0/device_calls0; generated examples are included. Historical61b evidence shows BMS/APK/signal absent and two stock libraries present. Preserve their bytes and metadata. Actual preinstall uses existing missing-only BMS and controlled empty placeholder creation, after user unseal and independent root authorization/lock. It stops at PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE; it never invents a UID or compiles an executable Boat plan.

## Capture interface gap: do not run the old scripts as a substitute

`outer/61b-v2-readonly-preinstall/capture.py` is a historical preinstall collector: it leaves UID null and always writes complete=false. `outer/61b-v2-readonly/capture.py` is also insufficient: it lacks strict `boat_identity` raw receipt triplets and strips cfg whitespace. Neither supplies the current provider contract unchanged. There is no valid existing61b postinstall CLI to list as ready.

The smallest successor is a separate parameter derivation of the already-used `final-v2-f28/capture5cd/capture_readonly.py`: replace its fixed serial and schema with61b and use the actual61b `capture.request.json` target/control/directory set. Keep expected-boot, full497+319 metadata, independent sameboot BMS UID receipts, exact cfg bytes, root absence and explicit remote rc unchanged. Do not substitute5cd paths/UID/WID. Its current CLI shape is `--out NEW --expected-boot REAL_BOOT` (preview) plus `--execute` only under later root authorization. This static delivery has not implemented or approved that successor; source pins identify the exact delta inputs.

## Compose after real postinstall capture

The following existing commands are ready once POSTINSTALL, BASE_CHECK and BASE_OBSERVATION are real sameboard evidence. No placeholder input is supplied or accepted here.

```sh
: "${POSTINSTALL:?actual complete61b postinstall capture required}"
: "${BASE_CHECK:?actual postinstall original R5 PASS required}"
: "${BASE_OBSERVATION:?matching R5 raw observation required}"
python3 "$P/board61b/provider/prepare.py" \
  --capture "$POSTINSTALL" --out "$OUT/boat"
python3 "$P/selfcheck/bind_request.py" \
  --template "$P/selfcheck/request.61b.pending.json" \
  --plan "$OUT/boat/plan.disabled.json" --out "$OUT/boat/request.json" \
  --base-selfcheck "$BASE_CHECK" --base-observation "$BASE_OBSERVATION"
python3 "$P/selfcheck/compile_selfcheck.py" \
  --request "$OUT/boat/request.json" --out "$OUT/boat/composed"
```

Output remains disabled, candidate/not_sealed:11 placements,7 binds,488 RouteB protections and expected954 union including Boat APK and private3. `planned_selfcheck.json/all_expected_sha256` is the T0 identity interface. For a changed host WID, bind_request's existing paired `--running-parameter-evidence REAL_EVIDENCE --current-boot REAL_BOOT` consumes independent sameboot host/WMS evidence; do not guess a WID or read it back from run.sh. OriginalV1 seal remains immutable. Root must separately bind completed full128, authorization, single-boot evidence and final live selfcheck before signing.
