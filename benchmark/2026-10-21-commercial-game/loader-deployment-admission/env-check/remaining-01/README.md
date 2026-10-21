# G19 remaining read-only stop applicability

**The original stop entry matches the system appspawn-x service, conditional on fresh identity and child quiescence.** No historical owned state is required. This is a source/receipt conclusion, not a performed stop or device admission. The G22 start-context repair remains with cx-env; this follow-up does not modify or re-review that implementation.

## What is already established

The preserved original config receipt (remote rc0) declares service `appspawn-x`, executable `/system/bin/appspawn-x --socket-name AppSpawnX`, UID root, ondemand true, and the AppSpawnX listener. Its file SHA is `5a499244840da582060a0d4db94fb769354b0d4f9e79bac56d4cf63414cfefb4`. This is the same service name targeted by `deploy_generation.py:249`: `begetctl stop_service appspawn-x`. The config capture belongs to boot `45339478-78d4-4211-ac17-6975440de5ce`; it is not silently promoted to a current a1d boot observation.

The newer saved G19 `outer-readonly-01` process table on boot a1d has one UID0/PPID1 appspawn-x candidate, PID6274, and zero direct children of that candidate. `parent-snapshot.json` records the exact original-parser output. This confirms the archived shape, not its continued freshness. PPID1 and a process name alone cannot distinguish the system daemon from a manually launched/reparented binary; read its actual exe and birth in the real window.

## Original stop behavior and exact minimum

`deploy_generation.py:40–41,242–253` first resolves BMS data and cold-stops **HelloWorld, Zigzag and Wikipedia**. All three bundles must resolve a UID; a missing bundle/failed parse is a concrete failure of this entry, not a reason to delete a control or skip the guard. It then rejects non-root processes named appspawn-x, calls the original begetctl stop, and polls up to 20 times at 0.2-second intervals for absence of processes with that name.

`bms_batch.py:613–664` implements each control cold-stop: `aa force-stop`, process classification by BMS UID and system parent exe, guarded signaling, then up to 15 seconds of target-UID survivor cleanup. The initial signal checks UID and PPID; later survivor signals recheck UID. The method does not check PID birth on every signal. This review does not strengthen these claims beyond the code, and did not invoke any of these writes.

The final `Deployment.stop()` guard selects `name == 'appspawn-x'`. A commercial-game child may have renamed its comm; the same original `cold_stop` comments explicitly acknowledge that condition. **The final guard alone is therefore not a full no-live-child proof.** Outer must inspect the complete fresh PID/PPID/UID table and current game UID/ancestry before allowing the stop. PID6274's zero-child historical snapshot cannot substitute. Process enumeration failure or an empty/unparseable result must remain an unknown, not a pass. Unknown live children are not an invitation to kill all matching processes.

The post-stop loop is conservative for additional processes still named appspawn-x: a root Route B peer or an ondemand respawn can keep it from completing. Do not work around that by generic killing, socket unlinking, disabling services or changing permissions. A bounded successful stop is only established by the original call and its actual readback during the authorized window. Prior configuration plus current matching identity makes this the appropriate existing entry; no new stop/launch wrapper is needed.

The precise remaining fresh fields are:

1. Current boot before/after, current `/system/etc/init/appspawn_x.cfg` hash/content, and `/system/bin/appspawn-x` SHA. The preserved config gives the intended name/path; confirm the real window still uses them.
2. Current unique system parent PID, UID, PPID, `/proc/PID/exe` path/SHA and stable `/proc/PID/stat` birth. Check all current direct children and test-UID helpers irrespective of comm. Do not read environ or reuse an old PID blindly.
3. Current BMS UID data for the three controls and Genshin, with complete rc0 process output. A control missing from BMS is an explicit preparation gap for this existing entry; no speculative missing bundle is asserted here.

`next-readonly-commands.json` lists the exact original `cat`, `ps`, `sha256sum`, `readlink`, `stat` and `bm dump` commands for those fields. They were **not executed by this follow-up**. Outer may consume equivalent existing fresh receipts instead. The file separates the write command `begetctl stop_service appspawn-x` from the read-only list.

## Dependency disposition, without another connection

All specifically inventoried local gate/script/recipe paths exist (`dependency-paths.json`); there is no claimed local missing file. The actual G20 SOURCE.txt matches its original LAB_HOME derivation regex; no hidden variable value was guessed or printed. Original `selinux_label_audit.plan_targets` accepted both assembly-02 native manifests: **15 declared label targets per package covering four required roots**. This checks the manifest input shape only; it does not apply labels or prove live labels. G22 must retain the original label recipe and correct candidate/baseline contexts.

The prior single G19 OrbStack timeout remains untouched. Outer readiness-01 originals are copied here: `orb -m a2hlab true`, rc0. Outer subsequently reports readiness-02 rc0 with Linux/Python3.12.3 and main/mac/readelf/shasum available, plus VM SSH-to-hw248 rc255 due to hostname resolution. Mac original oatdump has passed. Outer has provided the existing seven-line `gles-bounded-window/oatdump-via-mac.sh` adaptation and will run the original U7 gate in G21 with it. These newer facts supersede a general VM-unavailable interpretation; this follow-up neither reopens the connection nor asserts that the VM SSH failure disappeared.

No remote test, HDC retry, device write, wrapper construction, source/permission edit, G14/T38 operation or G20 assembly was performed. Original G19 env-check (29 files, landed e98e1b5a85) is unchanged; this directory is an incremental addendum. Existing window/rollback CLI and deadlines remain in the parent report, subject to G22/G21 acceptance. No deployment authorization is issued here.
