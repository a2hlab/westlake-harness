# COMMERCIAL-G03 — official Genshin (CN) install input (status: LOCATED; runtime NOT_TESTED)

Contract: `specs/commercial-game-round1/t3-official-input.spec.md` @ `85b30b0f2`. Device ops 0, no install, no login,
no APK execution, no REA. One official download (513 290 344 B ≤ 2 GiB). The APK lives only in the private dir.

## What was wrong first (kept)

- G01 found no Genshin input anywhere searched and macserver was unreachable; the only way forward was the official
  public entry. The legacy `ys.mihoyo.com/main/` pages are old pre-registration content and were not used.
- `h01` HEAD on the official porter link returns **HTTP 405**; kept as a failed receipt. Size was taken from a
  1-byte range GET (`h03`, 206) instead, before committing to the download.
- The Android URL was derived from the production branch in captured official JavaScript. The page runtime
  branch selection was not observed. The derived official porter returned an observed 302; no CDN version path was invented.

## Source chain (`source-chain.json`, extracted by `tools/chain.py` with offsets into the originals)

1. `https://ys.mihoyo.com/` loads puzzle page `config.aac69b9b.js` and `setups.32e271fc.js` (act.mihoyo.com).
2. config places `@puzzle/ys-download` v1.23.0, alias 安卓下载, `options.type = "android"`.
3. setups webpack runtime: `c.p = https://act.mihoyo.com/puzzle/hk4e/pz_Bw8DOTSoZy/`, `c.u()` maps chunk 14 to
   `14.fd07d37d.js` (also fetched: `lib.pc.ff966963.js`, `lib.m.5766697d.js`, 696 B stubs).
4. chunk 14 `downloadUrl` → `Zt()`: `Ht.production` overridden to `https://ys-api.mihoyo.com/event`,
   `Ut.production = ys_cn`, Android with no `from_channel` → channel `backup319`
   ⇒ `https://ys-api.mihoyo.com/event/download_porter/link/ys_cn/official/android_backup319`.
5. GET without redirect follow → **302** `Location:
   https://autopatchcn.yuanshen.com/client_app/download/Android/20260915143557_znpK0stDcvvXlIk8/ydbackup319/yuanshen_7.1.0.apk`.
   Downloaded from exactly that URL: HTTP 200, 54 s.

Assumption kept explicit: `globalOptions.environment = production` (deployment host); the assignment site was not
located. Only `production` maps to a public `ys-api` host.

## Input identity (`input-index.json`)

| Field | Value |
|---|---|
| SHA-256 / size | `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc` / 513 290 344 B (= Content-Length) |
| ETag / Last-Modified | `"llBtDuws3OZAUsC6-i-lTBXWEw5T"` / Tue, 15 Sep 2026 06:43:42 GMT |
| ZIP | `unzip -tqq` rc 0 (all CRCs ok), 1567 entries, 5 dex |
| package / version | `com.miHoYo.Yuanshen`, versionCode 1241, versionName `7.1.0_48052158_48145775` |
| SDK | minSdk 23, targetSdk 36 (compileSdk 36) |
| ABI | `arm64-v8a` only (32 native libs; largest `libyuanshen.so` 361 798 968 B) |
| launchable activity | `com.miHoYo.GetMobileInfo.MainActivity` |
| signature | `apksigner verify` Verifies; v1 + v2 true, v3/v3.1/v3.2/v4 false; 1 signer; DN `CN=Genshin Impact, OU=TianMing, O=miHoYo, L=Xuhui, ST=Shanghai, C=CN`; cert SHA-256 `f2d8dcdd…3b4a49`; 61 warnings for unprotected META-INF metadata entries |
| splits | none: no `split=` in badging, no `uses-split` / `requiredSplitTypes` / `isSplitRequired` in the manifest |

## Stage tiers

- **install-set:** COMPLETE per manifest — one universal base APK, no split declarations.
- **startup-assets:** UNKNOWN. The base bundles `assets/bin/Data` (~284 MB, incl. `Managed/Metadata/global-metadata.dat`)
  and `assets/AssetBundles/blocks` (~244 MB); which of them first start needs is unproven until a real startup-chain scan.
- **full-content:** NOT_ACQUIRED (post-install game resource download; out of scope, size UNKNOWN).

Engine is not asserted: there is no `libunity.so` / `libil2cpp.so` by name; the IL2CPP-style metadata file hints at
Unity IL2CPP but that is unverified. Small-app smokes (BoatAttack etc.) are not Genshin admission.

## Next action

Static-scan lane (Codex/OC) takes SHA `abd3c4d5…`: startup chain, JNI, DT_NEEDED, GLES/Vulkan, then derive
startup-assets. Any board run needs a separate outer contract; do not fetch full content under this card.

## Files and reproduction

`results.json` (status, elapsed, budget, limits, unknowns, 15 receipts with aliased argv / rc / sha256 raw refs, tool SHAs),
`input-index.json`, `source-chain.json`. Tools: `tools/rec.sh` (recorder, private root via `COMMERCIAL_G01_PRIVATE`),
`tools/chain.py`, `tools/inspect.sh` (sha256 / stat / unzip -t / aapt2 badging + xmltree / apksigner / zipstat),
`tools/zipstat.py`, `tools/gen.py`. Raw receipts and the APK: `$COMMERCIAL_G03_PRIVATE` =
`$HOME/.local/share/westlake/commercial-game-20261021/official-input/` (APK made read-only). Check:
`cargo test --test commercial_game_official_input` in `tools/spec-checks` (re-hashes the private APK when present).
