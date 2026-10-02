# LibreSudoku reuses the approved ICU zero-init candidate

The earlier standalone Java country fallback proposal would duplicate an already
prepared native repair. **Static path match: covered by 1e206531, predict one
first-fatal movement; do not build another library.** Next fatal and t20 unknown.

## Evidence, not a similar exception label

- Actual window5 PID 9435/TID 9459: original hilog **38564–38569** is null
  `String.isEmpty` in `Locale.getDisplayName:2539`, reached from ArrangementKt
  getDisplayName/getLangs/getCurrentLocaleString/WelcomeScreen. APPSPAWN **38691**
  records exit code 0 after its app exception handler (`evidence/hilog.txt`).
- Exact deployed core-oj SHA **e5b18770…**, tied by the original boot fingerprint,
  is decoded in `dex.json`: getDisplayName **DEX 0x64** invokes getDisplayCountry,
  **0x68** invokes String.isEmpty on that returned country. Debug position 0x68
  is line 2539, with local `displayCountry` in register 7. Thus this is country,
  not an unrelated language/Compose null.
- The same DEX getDisplayCountry calls LocaleNative.getDisplayCountry at
  **0x1b**, repeats with Locale.getDefault at **0x25**, then returns register 2
  directly at **0x29**: two null lookups can reach the fatal without a fallback.
- Local approved source excerpt (`evidence/scopedicu-source.txt`) shows
  LocaleNative_getDisplayCountryNative constructs **two** ScopedIcuLocale objects;
  invalid constructor -> NULL. Uninitialized UErrorCode is exactly the shared
  defect tracked by cc-wiki. Local source and already-built artifacts suffice;
  no new a2hlab/hw248 lookup or guessed source reproduction is needed here.
- Independently hash-checked the draft's existing candidate
  **1e206531ad5994b7d3fe332a050d53163a8ab5cf954b9314d748d7ff2ae8ae8f**.
  Its constructor at **0x12b9c** zeros the err slot with
  `str wzr,[x29,#0x1c]` at **0x12c08**, before forLanguageTag at **0x12c40**.
  Country function **0x144d0** calls that same constructor. Full exact ELF ranges
  are captured; no source-shaped placeholder assembly is substituted.

## Static gates and delivery boundary

`deployed_whois` first pins historical U9 owner /system/android/lib64/libicu_jni.
Actual current-generation deployment bytes are independently **4261c09eeda033f3…**.
open_site_scan of old/candidate: **0 sites, 0 namespace edges**, no MULTI-NS or
DEFAULT-NS. Strings old/candidate: **5 drop / 4 add**, reproduced verbatim in
`evidence/strings.txt`; those are the previously accepted ICU provenance/vendor
logging deltas, not a second patch from this lane. cc-wiki owns the source/build
closure and two-build receipt; this delivery adds only the coverage prediction.

Static linkage is strong evidence of a shared root path, not observation of the
actual garbage status value or proof that all possible NULL causes disappear.
Same-PID same-country null under verified 1e206531 refutes complete coverage.
Do not claim a new lit screenshot. Add this key to the existing ICU observation
group, not a separate ICU swap. Existing rollback is exact deployed
**4261c09eeda033f3de8a083ffd8896058ddcfc83d4f109990c0e680862591a1c**.
`results.json` carries confirm/refute and execution_enabled=false.

Reproduce offline: `collect.py`, `test_coverage.py`; original run and ELF hashes
are in results, raw command output stays in `.artifacts/`, portable copies in
evidence. No device command, draft/live package edit, new candidate or deployment.
