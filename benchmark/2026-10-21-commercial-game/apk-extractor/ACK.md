# ACK COMMERCIAL-G08

Status: OFFLINE_SOURCE_REPRO_AND_BOUNDARY_TESTS_PASS. Expected first blocker key: genshin only. Device install with patch: NOT_TESTED; game: NOT_STARTED.

- Actual first error: install-hilog line281 `CheckEndDir:71 endDir.numDisk != 0`; resource HAP succeeded at280. Exact original APK SHA/size unchanged.
- Real EOCD513290303/comment19/numDisk0; legacy EOF−22 read513290322 produces numDisk44712. Exact deployed51e1 ELF/outer REA agree with saved source. Nonzero comment must be accepted as well as located.
- Final candidate source SHA: `4068fdbae99b602062311b1f477b14b8702b07814bba44d09ffdbfa792c601c1`.
- Peer counterexamples fixed: 64-bit CD end <= EOCD-relative position; complete candidate validation with continued backwards search. Old3ab candidate/replay and failures retained.
- Actual final host replay: original/fixed × exact APK/control/truncated =6 calls. Original exact rc2; revised exact rc0/1567 entries; controls preserved. Additional8 boundary inputs ×2 original/revised =16 calls. Exact peer bytes included as hex.
- Actual final receipt check rc0 and Rust selector1PASS/0ignored. Spec lint100% rc0; Git frozen gate8entries/30checks/0violations (performed at final verification, not retroactively asserted as pre-build gating). User-path gate0 violations.
- No device calls, no production DSO, no APK alteration, no push. No Git permission retry; outer may commit the precise listing. No commit claimed.

Public handoff: `landing-paths.txt`, `SHA256SUMS`, `manifest.json`. Manifest payload231 files; complete landing235 files including four control documents. Manifest SHA: `32059bcef0777456aadf0e21ed7fa6618242cf68e495b9f3b8a0cf2161ec9a1c`.

Private original argv/stdout/stderr/rc: this packet `.private/replay-03`, `.private/boundaries-03`, `.private/static-01/02`, `.private/revision-02`. Final checks listed below remain private, exact bytes. External REA executed_by=outer(codex), inner analysis only; six raw references in evidence/rea-ledger.json. No remote archive claimed.

```json
[
  {
    "path": ".private/final-checks-01/receipt.argv.json",
    "sha256": "fe047774037c92acffaeb3ed7cd4cab4a95fd07527ef9d19eaef441ef741ed19",
    "bytes": 140
  },
  {
    "path": ".private/final-checks-01/receipt.rc",
    "sha256": "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
    "bytes": 1
  },
  {
    "path": ".private/final-checks-01/receipt.stderr",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "bytes": 0
  },
  {
    "path": ".private/final-checks-01/receipt.stdout",
    "sha256": "81ca27e0875950d925a414214e85bfefd7aa3efb43abd52edb7d748ba22ce0f5",
    "bytes": 114
  },
  {
    "path": ".private/final-checks-01/rust.argv.json",
    "sha256": "9483329ea38f5c30195fc8bfecfd804b9eb0cbd12298ff1572d8e9d2a92af87b",
    "bytes": 126
  },
  {
    "path": ".private/final-checks-01/rust.rc",
    "sha256": "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
    "bytes": 1
  },
  {
    "path": ".private/final-checks-01/rust.stderr",
    "sha256": "f8d8b50f32df11d8e5606bc62f95695a07218fa7e7f79ce7be4081b50b3d9098",
    "bytes": 447
  },
  {
    "path": ".private/final-checks-01/rust.stdout",
    "sha256": "bb395743860653b340139be51ec5bd71bcf75508f546c13bcaa5b80d6144c23d",
    "bytes": 276
  }
]
```

Next step requires an independently reviewed installer build and actual native-extraction validation; this offline card does not grant device deployment.
