# T39 final path-only delta review

**PASS within offline callback scope: 16 author callback tests + the unchanged 2 independent supplemental cases.** Both Node processes returned rc=0 with empty stderr. The previous `snapshot-97894eb0` is preserved; none of its passes substitutes for this new execution.

Frozen author files:

| File | SHA-256 |
|---|---|
| sources/candidate/EntryAbility.js | fc0e5ec024d34b27e56ac9841eb2cae9a5dd95de84d4da72c71418e1cfae0e56 |
| observer.fragment.js | 53a3489a2db042707372fc5f3bd102f431d5f852717f41a255c93cf8028bf0a1 |
| test_callbacks.cjs | 317d897d99c38484017a160b050e307648fc561e1dede495f23e8882a9c71022 |
| sources/baseline/EntryAbility.js | 9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6 |

`results.json` records captured/source-before/copy-before/source-after/copy-after SHA for every copied author file; all five values agree per file. The observer fragment is embedded byte-for-byte (ignoring only its trailing newline) in the candidate. Binding is by path and SHA only, as requested; no author Git ref operation, commit attempt or wait occurred.

`candidate.diff` contains only the new launchHomeAction helper accepting both `ohos.want.action.home` and `action.system.home`, and the corresponding call replacing the previous single-alias comparison. `tests.diff` contains only two whitelist callback cases. Both call real candidate onNewWant and assert home classification plus the common record checks, including manual_origin=unverified and eligible_for_reentry=false. No identity/authority logic changes. Light baseline and original lifecycle remain the same.

The exact new candidate was evaluated in the copied Node VM harness. The independent supplemental file is byte-identical to the previous review and reads the new candidate from this directory. It again checks partial-write plus unlink-failure recovery and onNewWant followed by foreground. No extra test scope was added.

Raw stdout/stderr/argv/rc and timestamps were captured during execution under `.private/`; public stdout copies, execution hashes and sizes are in results.json. Raw stderr remains private per AGENTS. Public frozen files are enumerated in landing-paths.txt and SHA256SUMS. No production/author file or old snapshot was changed; no device, VM, REA, deployment, permission or T38 work occurred.

No blocker found in this delta. Limits from the earlier review remain: mock native APIs do not establish real filesystem/power-loss behavior, and the latest-record slot is not a complete history. Observation is not proof of manual origin, reentry eligibility, white-screen repair or device acceptance. Outer owns landing/commit.
