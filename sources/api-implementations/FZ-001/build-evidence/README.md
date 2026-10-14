# Installer background-start and launcher selection

The CE repair exposes the next shared wall: Gallery and VLC successfully call
CommonEvent and then receive OH `START_ABILITIES_FROM_BACKGROUND` permission
denial. cc-wiki independently captured the same denial for Wikipedia's
onboarding activity. The installer source change is owned by cc-wiki; this
work combines it with the already tested launcher selection from cc-t3.

## Source and baseline

- Accepted network baseline: libbms 6f94d4f4 / libapk_installer eb6824b4; retain
  INTERNET and ACCESS_NETWORK_STATE mapping, the 1 MiB manifest buffer,
  XML-only icon fallback and the unchanged APK inputs.
- Launcher patch copied verbatim from cc-t3 commit 3188a4733; both install-plan
  selection and BMS mainAbility use SelectLauncherActivity. Four upstream
  host cases pass, including LeakCanary first/last, foreign-only fallback and
  no launcher.
- Compiler and persistent B79/B89 build inputs are documented in
  ../2026-09-29-bms-network-permissions/README.md. Installer output is isolated
  in bms/src/.work/installer-background-launcher.

## Deployment ownership

5ea remains owned by cc-wiki. The package uses Mac direct DevEco HDC and
requires the cc-wiki board lock. It backs up both service libraries at both
aliases, verifies backup SHA, replaces the pair, and supports exact rollback.
Announce the foundation restart on the board before applying. Device outcome,
ATM grant state, screenshot verdict and alive counts remain unverified until
cc-wiki executes its acceptance run.

## Original APK launcher check

The real Anki APK declares IntentHandler and LeakLauncherActivity; the new
selector chooses `com.ichi2.anki.IntentHandler`. Wikipedia keeps DefaultIcon
and Noice keeps MainActivity. The first test incorrectly reused the synthetic
fixture's IntroductionActivity name; `fixture-name-mismatch.txt` records that
failed test assertion. The corrected test checks the contract (own package
launcher) and prints every actual candidate; no production code changed to
satisfy the test. `real-apk-launcher-test.txt` records all three original APKs.

## Built candidate and host evidence

- libbms.z.so **6aadb8b4**; libapk_installer.so **7048c7c5**. Full SHA and
  accepted rollback pair are in manifest.json; HANDOFF.md gives guarded commands.
- cc-wiki's ACL/preAuthorization block is unchanged; APL_NORMAL and
  isSystemApp=false remain. The HAP writer adds the same background request.
  Old-token comparison includes the new permission, rejecting stale upgrades.
- The first build inlined away IsAndroidLauncherActivity's weak export.
  Marking that existing helper used preserves its ABI; the final pair has
  identical dynamic dependency order/SONAME/flags and imports, with no removed
  exports. The first failed ELF gate is retained in elf-first-build.json.
- Actual Wikipedia/Noice resource HAPs contain their two network permissions
  plus exactly one background-start request. Old production source fails the
  new expected-permission assertion (negative control, exit 134). Four guarded
  deployment tests pass, including partial failure rollback and wrong hashes.
- Known-answer tests: 69 run, 2 skipped, zero failures. B8 lifecycle: six Skip,
  zero selected tests, not acceptance. Board #80 follow-up explicitly authorizes
  this installer work beyond the generic B8 scope; no spec was changed.

Source snapshot, exact delta, recipes and outputs are in archive.json's archive.
Restore the persistent B79 base kit, apply base_bundle_installer.patch to its
B89 network baseline, copy apk_network_permissions.h alongside it, and run
build-bms.sh in the cloned kit. Installer build-installer.sh uses its isolated
adapter tree. Toolchain SHA and the original base archive SHA are recorded.

No board writes by cx-t0 in this handoff. ATM grant state and screenshot
acceptance remain unverified until cc-wiki's device test; R2 partially.
