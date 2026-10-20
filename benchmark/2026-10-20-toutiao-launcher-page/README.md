# Exact Toutiao host page candidate (offline)

The generic modern app recipe was not proof of the installed host. This package instead starts from the actual 53,303-byte `df385638…` HAP read by root, which is identical to the historical 5cd installed and signed HAP. All nine members were checked. The historical unsigned member inventory matches eight members; its `.pages.info` became the already recorded signing metadata.

The original Linux compiler `d20db2d4…` reproduced **both** original ABCs byte-for-byte. Root ran the provided `compile_abc.py` through its available offline tool channel. The new Index has SHA `3d98dbfb8a8cf35197c489c3af11285800ea9d2be877786d18bb2ae8f14a0fd3`, 2,388 bytes. The sole source delta removes the development title and keyboard text input. Original Column layout/background remain, and **EntryAbility is not changed**. Its existing window/lifecycle and the retained guardian still provide one normal icon → host window → Android child → feed. No direct Android shortcut, extra spawn or timing optimization is introduced.

Actual signed candidate: **`b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`**, 54,215 bytes. Signed payload difference is exactly `ets/pages/Index.abc`; all other eight members, including `.pages.info`, resources, icons, module and EntryAbility, are identical. The original and candidate extracted certificate chains and profile files are identical. The profile is the pinned public OpenHarmony development release profile with `apl=normal`, unchanged ACLs/permissions, bundle, versionCode2 and API20. These checks do not prove an installation or visual acceptance.

See [closure.json](closure.json), [compile-linux-01.json](compile-linux-01.json), [production-01.json](production-01.json), [inputs.lock.json](inputs.lock.json). Public raw command views are under `evidence/`; original unmodified raw, signed/unsigned HAPs and exact rollback HAP are under `.private/production-01`. Private inputs and historical sign logs remain under `.private/inputs-01`. `raw-index.json` pins local persistent originals and root's compile/intake records without publishing personal paths.

## Reproduce offline

1. Run `compile_abc.py --compiler "$EXACT_LINUX_ES2ABC" --out "$FRESH_ABC_OUT"` in the existing Linux environment. See [ROOT-COMPILE.md](ROOT-COMPILE.md). Inputs and compiler must match `inputs.lock.json`; baseline mismatch refuses before candidate compilation.
2. On a host with the pinned signer/public upstream dist and a recorded JDK:

```sh
python3 "$PACKAGE/package_sign.py" \
  --intake "$INTAKE/installed-entry.hap" --compiled "$FRESH_ABC_OUT" \
  --profile "$HISTORICAL_SIGNED/profile.p7b" --signing-dist "$PUBLIC_SIGNING_DIST" \
  --signer "$PINNED_HAP_SIGN_TOOL" --java "$JAVA" --out "$FRESH_SIGN_OUT"
```

The program copies the exact rollback HAP, verifies original HAP/profile, replaces only Index ABC, signs using the **original signed profile**, verifies candidate signature, and rejects certificate/profile/member drift. The public sample-key password is part of the upstream development credentials, not a private production credential. No keys are generated or new permissions requested.

3. Run `python3 "$PACKAGE/test_candidate.py" -v`; Rust selectors `launcher_page_closure` / `launcher_page_negative` call these real tests. Current result:12 Python tests and2 Rust selectors passed. Source/runtime frozen checker was run with `--git MAIN`:8 entries,30 checked,0 violations (see raw index). No old runtime/source file was changed.

## Preserved failures / scope

- Available Mac compiler compiled both old JS files but produced different ABCs; these are not released. Exact Linux replay closed that gap.
- Orb read-only path probe timed out; Docker socket was denied. No service restart or permission change. Root used its existing tool channel.
- Initial signer help flag was unsupported; initial verification output extension `.pem` was rejected. New `.cer` verification succeeded with original failures retained.
- Initial publishing command had a syntax error, so the first test missed its public receipt; corrected publication/tests are separate. No production compilation changed.

The candidate is **OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED**. Removing controls does not mean zero cold-start wait or faster first frame. HAP install can recreate the OH host window: root must independently bind fresh WID/parent and preserve T31's current candidate runtime. HAP rollback is separate from the six-state runtime rollback. No HDC, install, reboot, clear-data or push occurred here. The follow-on t3 contract/card is a separate root-only execution proposal and does not hold up this candidate.
