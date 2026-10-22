# T46-P2 — read-only member bytes for the 5cd restore-v1 ROOT

5cd, boot 8b64b087, no lock holder. Device writes 0. 20 s, 27 commands, each with argv/start/end/stdout/stderr/rc kept
and its body checked: every recv output contains `FileTransfer finish`, and there were no errors or denials.

- **Control inputs, 9 files**: stat+SHA lines are byte-identical to T46-P. No drift.
- **Control chain**:
  - init cfg 19d0201b → `boot-entry.sh` 7fbfdf05;
  - `startup.expected.sha256` content = sha(`startup.env`) = 44993dbc;
  - `members.tsv` 328f0af2.
- **All 13 `members.tsv` members**: device SHA = manifest SHA, device mode = manifest mode, and local bytes SHA =
  device SHA.
  - The 9 new members' bytes were received this round; the other 4 come from the T46-P bytes.
  - 12 SHAs equal T45's per-boot listing. `decoder-probe.jpeg` (e8320bdd) was not in T45's script listing; its bytes
    are kept private only.
- **Stability**: pre- and post-read stat for all 18 paths are identical.
- **Missing**: none of the 13 members.
- **Out of scope, not collected**:
  - the per-boot `boots/<boot>/` copies;
  - ROOT files that are not members (`cfg-rebase-*`, `cfg-stage-*`, `recovery.cfg`, `rollback-inert.cfg`).

The 9 new members (device SHA = local SHA):

| member | SHA-256 |
|---|---|
| launch-common.sh | d065f354392096819c93c808b89205355d62b333ff115fbadb8b9db38cbaa507 |
| real-start-parent.sh | 22ca89574f022322d2de8b6f6415d8bf10a557cea90e4e567145918d1c7a49f3 |
| real-spawn.sh | 46337ba8364d871c19fb077e29a4087f37921bf609c70e9f3c1f98e1fff124a3 |
| start-parent.sh | e00e5889283de3ee63038a85e6ea7a9a2d7cb765da30e8c800bbfa551d21f910 |
| spawn.sh | 5310fa014fd8fc5116318b25299f08f13d703d356a0bd0671fd722acb7c1f5c2 |
| screen-gate | 0bf966d76e038379af1fa2542746572a2c76a9bf88e17a97869682debfc36eaf |
| decoder-probe.jpeg (private) | e8320bdd8a81c3fd6a29a2fa39a1468ad515f1332ae51ebebdd13c4d0703b964 |
| real-start-parent-bounded.sh | fc0444a42b9b9ab9a70605944ad5b2ccad53e24c6b2a20ad730920f17dce898f |
| readiness-probe.sh | 2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717 |

Not claimed: rollout-ready, rollback prepared. Full per-member stat is in `members.json`.

Private raw: `$HOME/.local/share/westlake/t46p2-member-inputs-20261022/`; the `MANIFEST.sha256` SHA is in
`members.json`.
