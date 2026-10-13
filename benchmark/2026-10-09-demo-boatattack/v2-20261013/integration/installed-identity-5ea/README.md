# Actual 5ea installed identity

The original full128 install-index references 61b installation receipts. Those
receipts cannot establish the current installed bytes on 5ea. The actual initial
5ea preflight has 117 matches, 10 missing packages and one Noice drift. It is a
negative input, never an admission or a successful128 result.

This offline compiler produces the original driver's index shape from actual
5ea observations. It does not install, launch, collect, call subprocesses, access
a device or change any driver/guard. Existing117 are **observed installations**;
the ten additions and upgrade must have their original successful installation
records. No existing installation is represented as newly installed.

## Request JSON (v1)

`request.example.json` is a structural template; every placeholder must be
replaced with a real full SHA256. All pins have exactly `{path, sha256}`. Paths
are `$WORKSPACES/...`, absolute evidence paths, or relative to the request file.
The template is not executable admission.

| Field | Required evidence |
| --- | --- |
| `schema` | `verified-installed-identity-request/v1` |
| `serial` | Exact5ea serial `5ea34a4500000000000000001123012c` |
| `boot_id` | Actual canonical UUID shared by this collection/install window |
| `manifest` | Pin of canonical demo-manifest.json, SHA7a262732…; exactly128 unique keys/packages |
| `initial.identity` | Pin of original117/10/1 apk-identity.json; used to classify which keys need real installation records |
| `initial.bundles` | Original BMS list reading; corroborates existing package registration |
| `final.identity` | Pin of final fresh apk-identity.json in the same rows format; exactly128 MATCH, package and expected/actual full SHA equal manifest |
| `final.boot_before`, `final.boot_after` | Actual bookend boot readings; same boot, time-ordered |
| `final.bundles` | Fresh BMS list reading between those bookends; every manifest package registered |
| `final.apk_reads` | One or more batch SHA readings between bookends; raw lines contain all128 base.apk paths exactly once with exact manifest SHAs |
| `installations` | Exactly the keys missing, drifted or not BMS-registered initially; no omitted or extra installation claim |

A **reading** has three pins: `receipt`, `stdout`, `stderr`. Receipt uses the
existing native-HDC or BMS command-log format: `argv` with exact `-t SERIAL shell`,
`rc` / `exit_code` / `transport_rc`, and `time` / `finished` / `finished_at`.
Receipts with a `remote_rc` must have zero. BMS/EXACT remote rc markers, when used
by the recorded command, must exist and report zero. Error stderr is rejected,
even when native HDC incorrectly returns rc0. Unknown is never absence.

BMS raw format is the existing `bm dump -a` output headed `ID: 100:`. APK raw
format is `FULL_SHA  /data/app/el1/bundle/public/PACKAGE/android/base.apk`.
The compiler parses these originals instead of trusting summary counts. If the
new collector has a different raw format, provide it for a narrow parser review;
do not manufacture normalized original evidence or alter existing logs.

Each installation entry has `key`, `record`, `output`, `boot_before`,
`install_command`, `boot_after`. `record` pins the **unchanged** actual install-only
record: status installed, exact5ea/key/package/APK SHA, success rc0, BMS queryable.
`output` is that record's original install.txt. The actual `bm install` command
reading must agree with it and contain the established success text. Install
bookend boot receipts bind the same boot and bound the command in time. This also
supports Pain's existing record, which has no embedded boot field; no boot is
invented in that record. Final full128 collection must start after every supplied
installation record's `finished_at`.

## Output and unchanged driver interface

```sh
PYTHONDONTWRITEBYTECODE=1 python3 compile_index.py \
  --request /path/to/actual-request.json --out /path/to/fresh-output
```

Any validation failure exits2 and writes no successful index. Validation finishes
before output creation. A success writes `install-index.json`, per-key
`records/KEY.json`, and pinned `receipt.json`. Index shape remains:

```json
{
  "KEY": {
    "success": true,
    "apk_sha256": "FULL_SHA256",
    "record": "$WORKSPACES/.../records/KEY.json",
    "record_sha256": "FULL_SHA256",
    "status": "verified-installed-identity",
    "error": null,
    "serial": "5ea34a4500000000000000001123012c",
    "boot_id": "ACTUAL_UUID",
    "package": "PACKAGE",
    "basis": "existing-installation-observed"
  }
}
```

`basis` is `existing-installation-observed`, `new-installation`, or
`upgraded-installation`. Per-key verification records bind the request, manifest,
final identity and original actual installation record when applicable. They do
not claim a fresh install for117, UI success, or rewrite original records.

Pass this new file via the existing full128 prepare `--install-index` argument.
Use a fresh round, since the driver pins this input. Do not patch a prepared round
or remove any existing identity/binding/128/special-slot guard.

## Offline evidence / review boundary

`tests.txt`: 12/12 PASS. Actual117/10/1 is rejected. The positive is explicitly
synthetic, creates117 observed +10 new +1 upgraded entries, and calls the unchanged
reviewed full128 driver's offline prepare with the result (128/eight windows,
disabled). Negatives cover missing install receipt, foreign61b record, raw SHA
drift despite MATCH summary, BMS missing, boot drift, pin drift, rc0 transport
error, late installation, missing member and missing remote marker.

Only compiler readiness is asserted. No actual VERIFIED index exists in this
package. Root's final fresh evidence and real installation records are pending.
T0 review: `compile_index.py`, this field table, template and focused tests.
