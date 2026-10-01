# Exact installer-selected icon formats (U8, 166 keys)

## What the earlier inference missed

Counting image files by directory or extension does not reproduce `ReadIconByManifest`. A `.webp` suffix does not prove valid WebP bytes, and a missing desktop tile does not establish that WebP is unsupported. This audit reads application `android:icon`, executes the unchanged SHA-pinned production resource resolver, and inspects only its selected resource file.

## Results

| Selected input format | Keys |
| --- | ---: |
| PNG | 130 |
| WebP family | 25 |
| XML | 11 |
| JPEG / missing / unresolved | 0 |

All 166 APK/package identities match the selected run records. Of the 25 WebP-family keys, **24 have a canonical RIFF/WEBP header and matching RIFF length, and all 24 have their own tile**. The remaining key, `cv2-com-frequent-habits`, contains malformed WebP-family bytes and has no own tile in the captured pages, including the signed retry. These are container-header checks, not a claim of successful full image decoding.

`ICONS.csv` is the compact per-key answer; `results.json` retains resource candidates, selected-byte hashes, original and supplemental signed outcomes, and exact own-tile witnesses with snapshot filenames and SHA256. The original full sweep has 163 observed own tiles, 1 searched-no-match and 2 cold-desktop unknowns. The supplemental retry resolves both cold cases: latest observations are 165 own tiles and 1 searched-no-match. Original screenshot signoff is 99 lit; incorporating the separately signed retry is 100 lit. Neither tile existence nor a header check is a UI signoff.

The 25 WebP-family keys are `fd-breezyweather`, `fd-catima`, `fd-fennec_fdroid`, `fd-filemanager`, `fd-gallery`, `fd-musicplayer`, `fd-notes`, `fd-tutanota`, `firefox`, `ooniprobe`, `x`, `cv2-com-degeder-yam`, `cv2-com-pep1lo-bakerspercentagecalculator`, `cv2-ca-ramzan-delist`, `cv2-com-simonimal-minimalcurconv`, `cv2-com-codedead-advancedpassgen`, `cv2-com-codedead-deadhash`, `cv2-ca-vaults-randomlydie`, `cv2-com-rootminusone8004-bazarnote`, `cv2-com-git-itdolan31-crystalpad`, `cv2-io-github-jdanders-dropcount`, `cv2-com-frequent-habits`, `cv2-com-edward-studytracker`, `cv2-com-armanmaurya-archiv`, and `cv2-com-caniwebview-android`.

## Frequent Habits: selected bytes are already malformed

APK SHA256 is `3b6cb46847c99fb82537e7fa3f0527f4443c544fa8a8839588c5ce32e368b446`, also the local authoritative F-Droid index's version-17 hash. Icon ID `0x7f090000` resolves to `res/d2.webp`, not the adaptive XML. Its 1485 bytes start `52494646c38e03000057454250565038580a00000010000000`: `WEBP` is at offset 9 instead of 8, and the encoded RIFF length disagrees with the actual file size. All five WebP configurations show the same reversible Latin1-to-UTF8 expansion pattern. In-memory diagnostic reversal of d2 yields 982 bytes with a matching RIFF length; **no repaired file or modified APK is produced**. The upstream producer of this corruption remains unknown. See `evidence/frequent-habits.json` for the five members and index binding.

The retry's `install-hilog.txt` confirms the selected member was read and 1485 raw bytes were written to `android/icon.png`; normalization skipped non-decodable PNG bytes. The own tile is absent across captured launcher pages. This narrows the failure to malformed selected image handling; it does not prove that the filename `icon.png` breaks healthy WebP.

## Resolver and observation boundaries

- Host compilation uses the unchanged `arsc_resolver.cpp` SHA256 `22b27c2e88b9763fc4843df3a17edf2941729084c8a6f97e8c4a7322490c7bb1`. Only minizip I/O and hilog are mocked; the probe consumes the exact extracted `resources.arsc` bytes.
- This resolver scores density substrings in file paths, penalizes XML, and preserves the first equal-scoring candidate. It does not select the Android device's best density configuration. Obfuscated raster paths therefore tie and the first resource-table member wins.
- XML describes the selected input. Later adaptive composition or legacy fallback may produce PNG, but is not relabeled as the selected file's format.
- `cv2-com-wbpxre150-shoppinglist` uses framework ID `0x01080034`, selecting `res/drawable-xxhdpi-v4/ic_menu_agenda.png`. The outer independently read the same framework-res SHA256 on all three boards: `76a157c084f9b90dae195191d2159901434f11f815e3e2d9eea02ded486e7770` (ACK97 14:41:10). It is outside runtime/boot fingerprints; the frozen expected map is not edited.
- The installer passes `artifact_identity` against the U8 expected artifact (SHA256 `7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18`). The separate framework SHA attestation is not misreported as an artifact-identity match.
- Own tile means exact package plus recorded desktop Activity under sceneboard in `icons-*.json`. Hidden/nonclickable witnesses remain distinguishable. Cold or absent snapshots are unknown; no match on searched pages is not global launcher-database absence.
- Only the six formal sequential run roots plus `5cd-seq-v1-rest` are used. The original full-sweep signoff and the four-key 14:23:37 signed retry remain separate columns.

## Reproduce

```sh
python3 benchmark/2026-10-01-icon-format-scan/test_scan.py
python3 benchmark/2026-10-01-icon-format-scan/scan.py --workspaces "$WORKSPACES" --output /tmp/icon-format-scan
```

Use `/usr/bin/clang++` for host probes and the installed Android build-tools 37.0.0 `aapt2`. No device writes, resource changes, or frozen prediction changes are performed. Validation and the additive landing manifest accompany this report.
