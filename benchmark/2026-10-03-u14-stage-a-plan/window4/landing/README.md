# U14 Stage A window 4: remaining reference protection

The dispatch prose called the reference registry `reference.json`; the actual checked 126-key registry is `benchmark/2026-10-03-u14-reference/sources.json`. Subtracting only keys with `lit_runs > 0` in the three signed window results gives 67 signed keys and 59 remaining. Seal is deferred until physical 61b recovery because its installation-chain prerequisite is absent on the online boards. The other 58 keys were assigned disjointly, 29 per online board. This is global Stage A key coverage, not admission of the offline 61b variant.

All four fresh production faces passed: Mac/VM × common/61b, N1 99 and N2 105 approved findings, zero rejects, static/frozen/RB/T4b/G1/G2/full executor checks passed. The first 61b-variant VM native N2 failed with `readelf did not describe a dynamic section`; its other checks and full executor passed. That face was rejected before LOCK. Its original evidence is preserved and one isolated bounded rerun passed using unchanged tools, package and criteria. The cause of the first readelf output failure is unproven.

5cd passed pre-lock first. The first 5ea pre-lock refused because vmgr exceeded 3 GiB, without acquiring a lock or writing the board. It passed a second complete pre-lock after memory naturally fell. No shared VM/HDC restart occurred. The exact gate-complete board line is 20281 (`U14窗4 门过`).

Both candidate activation smokes passed. The regular sampling produced 17 records on 5cd and 16 on 5ea; these are observation counts, not UI verdicts. Twenty-five online keys remain unobserved, plus Seal on offline 61b. Each board stopped new keys at its approved 35-minute cutoff. Only a direct owned batch child for a post-cutoff, zero-record shard received SIGINT; neither an in-flight capture nor the runner/finish was interrupted. Both unchanged runners executed unconditional restoration.

Both boards restored U13 within their 45-minute windows: 321 assertions over 319 paths, empty diff/absent, runtime `821de739cf81`, boot `ee927db88a67`, parent/child view and recovery HW/ZZ smoke PASS, locks empty. No window-4 device command targeted 61b; its window-2 journal and lock remain pending physical reconnect.

Schema-2 process selftest counts are zero for selftest_error, badtag, probe_error and unknown among actual records. Empty reports are retained separately as unmeasured, never as process PASS. Facts and screenshot paths are provided for outer ground-truth review; no lighting or regression conclusion is asserted here.

Small landing copies normalize workspace paths. The archive receipt binds all raw, unnormalized captures, complete gate/retry outputs, manifests, logs and transaction evidence. Originals are retained at the execution paths.
