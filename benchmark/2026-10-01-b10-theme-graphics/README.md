# B10: ActionBar themes and graphics native constructors

The earlier startup-only lifecycle scan missed `onPostCreate`: seven additional
later-Activity theme candidates were hidden in inherited Secuso BaseActivity
methods. A theme named NoActionBar also does not prove that its Android and
AppCompat attributes agree. The new rule scans every DEX, includes inherited
onPostCreate/onPostResume, resolves local style variants, and separates static
call/contract candidates from an actually observed crash and from frame timing.

## Evidence and baseline

- **166 keys, 166 exact APK SHA, 165 packages, 350 DEX members**. Old inputs are
  the 66 keys from apps.json, admitted against frozen U7 inputs.json; new inputs
  are the 100 corpus-v2 APKs. Every APK hash and manifest package was checked.
  `fd-noice` and `noice` share a package, but their frozen APK bytes differ.
- DEX coverage is the selected frozen APK, not arbitrary dynamic/split code.
  Burger King, Firefox, McDonald's, Subway Surfers and X have split-input hints;
  their frozen sidecar inventory has no APK/ZIP/JAR/DEX member to scan separately.
  Missing future code or reflected/obfuscated dispatch remains unknown.
- Whole-DEX counts: **297 literal setSupportActionBar calls, 4099 graphics
  constructor/native-family references**. References inside uninvoked library
  methods are not silently counted as actual app execution. The graph is bounded
  to eight exact-owner/inheritance-resolved edges; dispatch, reflection, R8 names,
  callbacks, branch outcomes and depth caps remain explicit unknowns.
- `facts.json.gz.b64` retains every callsite (DEX hash/member, method, offset,
  dump line), local resource/style/config witnesses, dynamic setTheme references,
  and lifecycle paths. Repeated style evidence is deduplicated, not call counts.
- **artifact_identity ran before native inspection and returned 0 / DEPLOYED**:
  U7 libhwui `be59260f93b3`, liboh_android_runtime `216b68fbb3a4`, framework.jar
  `3e106350d882`. Expected-run SHA and tool SHA/stdout are in
  `native-constructors.json`. This is U7, **not** a claim about N10/J8/T7e.
- Native bodies come from these exact ELF function/table addresses, not a similarly
  named .so or a donor tree. Source slices aid class-table attribution only.
  `native-constructors.json` includes normalized disassembly, symbols, direct throw
  branches, framework Java-to-native initiation sites, and all 23 creation APIs.
- `calibrations.json` contains three target-PID, hash-bound terminal-first results
  from the **later cv2-hilog diagnostic run**. They match outer ACK(97)
  `2026-10-01T10:24:59+0800`: Memory/Yahtzee ActionBar conflict and Acrylic Emboss
  constructor IAE. These do not replace the earlier signed cv2 t20 observations.

## ActionBar impact: two triage tiers, with uncertainty

52 apps have non-library-only literal ActionBar references. **49 keys** have
an Activity context whose local style variants explicitly suppress ActionBar.
AppCompat `windowActionBar=false` and `android:windowActionBar=false` are stored
separately; external framework parents, conflicting variants and dynamic themes
are not guessed. NoActionBar is the **correct contract**, not itself a defect.

| Primary triage tier | Keys | Meaning |
|---|---:|---|
| Startup/first-content | 21 | 19 bounded startup call/NoActionBar candidates + 2 separately calibrated first-content failures |
| Later-Activity only | 28 | No startup-tier witness/calibration, but later Activity lifecycle contains the call and NoActionBar contract |
| Signed functional-lit within later-only | 22 | Latent later-screen candidates; not 22 proved future crashes |

Both primary key lists are in `results.json/actionbar_cluster/two_tier_schedule`
and the per-key `actionbar_schedule` CSV column. For the complete scope rather
than mutually exclusive triage: 19 startup keys, 43 later-Activity keys, **13
overlap**, and 30 signed-lit keys with some later-Activity candidate. There are
also 17 keys with some unanchored references, overlapping those lists; their
unresolved sites remain in the table rather than being declared safe or late.

The 22 signed-lit **later-only** candidates:

- `cv2-com-benny-pxerstudio`, `cv2-com-example-dozencalc`.
- `cv2-org-secuso-privacyfriendly2048`, `cv2-org-secuso-privacyfriendlybattleship`,
  `cv2-org-secuso-privacyfriendlycircuittraining`, `cv2-org-secuso-privacyfriendlydame`,
  `cv2-org-secuso-privacyfriendlydicer`, `cv2-org-secuso-privacyfriendlyintervaltimer`,
  `cv2-org-secuso-privacyfriendlyludo`, `cv2-org-secuso-privacyfriendlyminesweeper`,
  `cv2-org-secuso-privacyfriendlynotes`, `cv2-org-secuso-privacyfriendlypaindiary`,
  `cv2-org-secuso-privacyfriendlypasswordgenerator`, `cv2-org-secuso-privacyfriendlypausinghealthily`,
  `cv2-org-secuso-privacyfriendlypin`, `cv2-org-secuso-privacyfriendlyrecknoningskills`,
  `cv2-org-secuso-privacyfriendlyruler`, `cv2-org-secuso-privacyfriendlysudoku`,
  `cv2-org-secuso-privacyfriendlytapemeasure`.
- `fd-catima`, `fd-libretube`, `fd-uhabits`.

**Timing boundary:** non-launcher Activity can run immediately after a splash,
before any visible frame. A first-run preference can select Welcome or Main.
Static reachability does not establish that branch, screen ownership or a timestamp
after t20. Only Memory/Yahtzee's diagnostic failures establish their first-content
case here. "Already lit" does not prove that every future toolbar call succeeds.
Conversely, already-lit startup candidates (e.g. Aegis/Markor/NewPipe) are negative
controls against a blanket NoActionBar + API-call rejection gate.

Memory's concrete witness: Splash is LAUNCHER; ui.MainActivity uses
`AppTheme.NoActionBar` with AppCompat `windowActionBar=false/windowNoTitle=true`;
MainActivity's onCreate reaches setupNavigationView/setSupportActionBar. Dame,
Ludo, Password Generator, PIN and Ruler use inherited **BaseActivity.onPostCreate**
in later Activities; omitting that callback loses these calls despite a full DEX
reference scan. Bizzle has no literal ActionBar call and is a signed-lit negative
control, not a proof that it has no dynamic or obfuscated equivalent.

## Graphics JNI: registration does not imply correct construction

| Compiled creation inventory | Count | Interpretation |
|---|---:|---|
| Class-attributed table/function matches | 16 | Static compiled registration proof, not evidence RegisterNatives executed |
| Table/function present, owning-class attribution unresolved | 7 | Unknown, **not missing**; BitmapShader, four ColorFilters and RuntimeShader nativeCreateShader |
| Unconditional normal-path direct throw | 1 | EmbossMaskFilter |
| Conditional direct throw | 6 | BlurMaskFilter, Linear/Radial/SweepGradient, RuntimeShader builder/create |
| No direct throw witness | 16 | No safety claim about callees, allocation, Java validation or arguments |

Coverage includes MaskFilter/PathEffect/Shader subclasses, gradients and adjacent
ColorFilters; destructors/finalizers/update methods are excluded from creation
counts. All 23 compiled function pointers are in libhwui; the identity-pinned
liboh_android_runtime was also inspected through the existing deployed JNI profile.
Actual runtime registration order/overrides are not reconstructed from mere strings.

### Ranked blocking result

1. **EmbossMaskFilter.nativeConstructor([FFFF)J** — **1 consumer key, 1 observed
   blocker: `cv2-anupam-acrylic`**. Its Java constructor eagerly calls native.
   `EasyPaint.onCreate` is a non-launcher lifecycle candidate; the later diagnostic
   confirms it is the first content Activity after Splash.
   The deployed function starts at **0x1434bc**; **0x1434fc** unconditionally calls
   `doThrowIAE`, then **0x14350c** returns zero. No function-local condition bypasses
   that call on the normal path. This is a registered-but-broken implementation,
   **not** a missing JNI method. Body/exception/DEX evidence is machine-linked.
2. **All other 22 creation APIs** — **0 proved unconditional blockers** from this
   audit. Conditional exceptions and missing class attribution require arguments,
   binding and execution evidence. The sorted table uses observed blocked keys,
   then unconditional callsite upper bound, then consumer-key count as a tie-break,
   never equating widespread library presence with thousands of actual failures.

157 apps contain some creation-family reference. For example, PorterDuffColorFilter
has 156 consumer keys and LinearGradient 155; these numbers are **references**, not
blocked/unlocked counts. Shader/ColorFilter native creation commonly occurs in
createNativeInstance/factory/drawing, after Java `new`; exact framework bytecode
initiation is included per native API. PathEffect/Blur/Emboss constructors are eager.
The ColorMatrixColorFilter case is not the JAR ColorMatrix wall: the identity-pinned
framework Java/native APIs and their source attribution are independently reported.

## Reproduce and hand off

```sh
python3 benchmark/2026-10-01-b10-theme-graphics/collect.py --output /tmp/b10-facts.json
python3 benchmark/2026-10-01-b10-theme-graphics/compact.py --input /tmp/b10-facts.json --output /tmp/b10-facts.b64
python3 benchmark/2026-10-01-b10-theme-graphics/native_audit.py --output /tmp/b10-native.json
python3 benchmark/2026-10-01-b10-theme-graphics/report.py --output /tmp/b10-predictions
python3 benchmark/2026-10-01-b10-theme-graphics/test_impact.py
```

Collectors use WORKSPACES, HOME and script-relative paths. Compact raw input and
audit files replace the corresponding checked-in evidence only for a new scan
version; all previous U7/cv2 freezes and scores stay unchanged. This artifact is
an offline retrospective impact prediction, not a new held-out freeze.
See `validation.json` for completed software gates and `landing-paths.txt` for
the exact outer handoff. Shared README/DIGEST additions are in documentation.json;
do not copy whole shared files. No runtime repairs, device writes or push.

### Gate result and unchanged baseline failure

- New Python checks: **11 passed**; contract lifecycle: **4 scenarios passed**,
  lint quality **1.0**. Isolated-master known-answer suite: **82 tests, 3 skipped,
  0 failed**. Full user-path gate: **exit 0**, 12156 files, 25 exceptions,
  no violations.
- Fixed master `548203909498d55940bd773dfd33452c0d93e05c`, with only this
  18-path handoff plus the two exact documentation additions, has spec_checks
  **exit 1**: cargo 101, 145 passed / 10 failed, 9 approved / **1 unexpected**.
  The clean fixed master has the **same** `native_landing_registry` failure:
  141 passed / 10 failed, 9 approved / 1 unexpected. All four added Rust checks
  pass; the failure is not waived or repaired here.
- The unchanged selector pins native-predeploy-exceptions.json to
  `d40f3b9d44d248fd6b7b665aa90b78bd35464db60e42ea90c275b1ce85d7a9da`,
  but the fixed-master bytes hash to
  `155f1bccdba877dc125a7ea8675d5461b9d0ae66180957a38ebc906c31d1e478`.
  Three initial N10 failures were missing sibling packages in the temporary
  checkout, not repository regressions; providing read-only package references
  restores those checks. Both clean/overlay comparisons use that same setup.
- Original v1 handoff **18/18** and earlier cv2 scoring handoff **24/24** are
  byte-identical to their committed baselines. The git add attempt exits **128**
  on shared worktree index.lock; outer must commit only landing-paths and exact
  documentation lines, not the old staged U7 skeleton.
