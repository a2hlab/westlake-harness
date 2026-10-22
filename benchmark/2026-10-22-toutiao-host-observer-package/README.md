# T41 — offline host-observer HAP packaging (EntryAbility-only, real sign/verify)

Assemble the T40-compiled passive host-observer bytecode into an independent, verifiable HAP by reusing
the **already-accepted b189 base** and swapping **only** `ets/entryability/EntryAbility.abc`. This card is
offline packaging only: **no device, no REA, no deployment, no reentry.** `device_calls = 0`.

## What was wrong first, and the rule this card sets

The first real signing was **correctly refused** by the original criterion, which treated `.pages.info`
as an unchanged application resource. That refusal is kept verbatim (persistent `public-01`, signed HAP
`d5c8f34e…` — the same artifact the outer loop independently re-derived from).

`.pages.info` is **not** a generic resource: upstream `PageInfoGenerator`
(`PageInfoExtension.DEFAULT_UNIT_SIZE = 4`) builds an **executable-page bitmap**. When EntryAbility grows,
its ABC spans one more 4096-byte page, so the bitmap deterministically flips one bit. The rule here is a
**single exact, SHA-pinned derived-metadata exception** (`t41-metadata-exception.json`, copied byte-for-byte
from master `5f80adf44`, sha256 `282d0703…`) **plus an independent layout re-derivation** — not a general
`.pages.info` allowance, not a signature bypass, not a retroactive pass of the first failure.

- bit set per occupied page = `page*4 + 1`, in an 8-byte little-endian bitmap.
- base: `EntryAbility`@off 4096 / 3244 B → page **[1]**; `Index`@8192 → page **[2]** ⇒ `20 02 00 00 00 00 00 00`.
- candidate: `EntryAbility`@4096 / **6644 B** → pages **[1,2]**; `Index` shifts to @12288 → page **[3]** ⇒ `20 22 00 00 00 00 00 00`.
- The checker recomputes this from the **real ZIP local-header offsets** of both HAPs and (purely) from the
  receipt's recorded page sets; both must equal the exception's `before_hex` / `after_hex`.

## Result (delivered build `release-02`, rc0)

| criterion | outcome |
|---|---|
| signing stages | `verify-base`, `verify-profile`, `sign-app`, `verify-app` all **rc 0** |
| program/resource content change | **only** `ets/entryability/EntryAbility.abc` (`bb1eccd3…` → T40 `db781436…`) |
| other 7 program/resource members | byte-identical (`Index.abc` `3d98dbfb…`, `module.json`, `ResourceTable.txt`, `resources.index`, `app_icon.png`, `icon.png`, `main_pages.json`) |
| `.pages.info` | exact exception `9e217e6b…`→`243cf95f…` (`2002…`→`2022…`), independently reproduced from ABC page layout |
| certificate chain | byte-identical before/after (`5358faac…`) |
| provisioning profile | byte-identical before/after (`87743d71…`), `verifiedPassed = true` |
| identity / permission / credential | unchanged — reused public dev cert + profile; no new identity/permission |
| device | none; not deployed |

**Whole-HAP SHA is not a pinned criterion.** The signature block carries a timestamp, so each sign produces a
different whole-HAP digest (`public-01 d5c8f34e…`, `public-02 b65a8cf3…`, `release-01 6f5e6a65…`,
**delivered `release-02 02f56d18…`**). The pinned, reproducible facts are **member-level** (EntryAbility, the seven resources, the `.pages.info` exception) plus
the byte-identical cert/profile.

## Reproducible recipe

All personal absolute paths and the keystore password are passed as arguments — **nothing personal or secret
is hard-coded** in `package_observer.py`. The password lives only in a private file (`--pwd-file`, same pinned
public OpenHarmony dev value T32 used; cross-checked equal to the T32 private `sign-candidate` argv) and never
enters this card. Output dirs must not pre-exist and are never reused.

```
python3 package_observer.py \
  --base        <b189 candidate-signed.hap, sha256 b18978b8…, 54215 B> \
  --replacement <T40 EntryAbility.abc, sha256 db781436…> \
  --java        <OpenJDK 21 java, sha256 d7ab2ea6…> \
  --signer      <hap-sign-tool.jar, sha256 91cea673…> \
  --signing-dist <oh-hapsigner/dist: OpenHarmony.p12 7a5efc3e…, OpenHarmonyApplication.pem b5c1d625…, …> \
  --pwd-file    <private keystore pwd file (not in git)> \
  --out-public  <fresh dir> --out-private <fresh dir>
```

**Execution provenance.** The committed `receipt/receipt.json` is produced by the committed driver
`package_observer.py` sha256 `075170c7…`, which signed **`release-02`** (signed HAP `02f56d18…`). The earlier
`release-01` (`6f5e6a65…`) was signed by a driver that differed only by a later-added `sys.dont_write_bytecode = True`
line (suppresses `.pyc` writing; inert to the sign/verify path); no old execution is attributed to the final code.

The driver: hard-verifies java/signer/dist SHAs (not just records them) → verifies the base HAP and extracts
its cert chain + profile (must equal the pinned `87743d71…` / `5358faac…`) → verifies the profile
(`verifiedPassed`) → rebuilds an unsigned HAP (ZIP_STORED, fixed 1980 timestamps, 0644) swapping **only**
EntryAbility → signs (localSign, SHA256withECDSA) → re-verifies the candidate → requires cert and profile
byte-identical → runs the shared `verify_candidate` (EntryAbility-only content change, 7 resources identical,
`.pages.info` under the exact exception + independent derivation). Full argv (incl. password), stdout, stderr,
rc and timing are streamed to the **private** dir; the card holds only redacted argv + rc + SHA pins.

## Verify

```
python3 check_package.py            # default --build-dir = persistent release-01
cargo test --test toutiao_host_observer_package   # from tools/spec-checks
```

`check_package.py` runs the **shared production verifier** against the real persisted HAPs (positive) and drives
that same verifier to refuse: an extra resource member change (`UNEXPECTED_RESOURCE_CHANGE`), a non-T40
EntryAbility (`SIGNED_ENTRY`), a generic `.pages.info` drift (`META_AFTER`), a `.pages.info` whose hex matches
the exception but whose ABC page layout does **not** reproduce it (`DERIVE_AFTER`), a changed member set
(`MEMBER_SET`), a tampered exception file (`EXCEPTION_FILE_SHA`), a foreign signer scope (`EXCEPTION_SCOPE`);
plus the driver refusing a reused output dir and missing args. These are real-code refusals, not assertion
helpers. No signing, device or REA runs in the checker.

## Layout

| path | what |
|---|---|
| `package_observer.py` | offline packager + shared `verify_candidate` (paths/pwd via args; no hard-coded personal path/secret) |
| `check_package.py` | production checker: real `verify_candidate` positives + mutated-payload negatives |
| `t41-metadata-exception.json` | the single exact `.pages.info` exception (copy of master `5f80adf44`, sha256 `282d0703…`) |
| `outer-policy/README.md`, `outer-policy/pages-info-derivation.json` | outer-loop independent ABC-page-bitmap derivation (copied from master `5f80adf44`, SHA-verified) |
| `receipt/receipt.json` | real `release-01` run receipt: member before/after SHAs, exception record, stage rc, `device_calls=0` |
| `receipt/raw-public/*.redacted.json` | public argv per stage — passwords `<redacted-secret>`, personal paths aliased (`<java>`/`<signer>`/`<signing-dist>`/`$HOME/…`) |
| `SHA256SUMS` | SHA index of the committed card files |

**Not in git** (persistent, binaries/raw logs): the base/unsigned/signed HAPs, extracted cert/profile, and the
full unredacted argv/stdout/stderr live under
`$HOME/.local/share/westlake/toutiao-host-observer-package-20261022/{public-01,release-01,release-02,release-02-private}`.
`public-01` is the kept first-refusal (signed HAP `d5c8f34e…`); **`release-02` is the delivered build** (signed HAP
`02f56d18…`, produced by committed driver `075170c7…`); `release-01` (`6f5e6a65…`) is the behaviorally-identical
earlier run. Raw file SHAs for the delivered run are pinned in `receipt.json → private_raw_pins`.

## Scope / non-claims

Offline packaging only. No deployment, no runtime, no white-screen or playback claim, no freeze, no device
state change. The outer loop's read-only preflight (5cd currently carries `entry.hap` with SHA == this base
`b18978b8…`) is **outer-loop context, not this card's execution**; this card stays `device_calls = 0`. Deliver
is **path-list + SHA256SUMS only — no git commit, no push.**
