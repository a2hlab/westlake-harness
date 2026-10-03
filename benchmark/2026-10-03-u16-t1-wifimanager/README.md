# U16 t1 — WifiManager 8 methods, "no Wi-Fi" semantics (oc-t4, offline)

Per `specs/u16-batch/t1-wifimanager.spec.md`. Base: U15 stubs `94a949053ec8c5a5`
(generations/u15-bt-bake-9e55-94a9-v1/jars9/adapter-mainline-stubs.jar, 276 classes).
Output jar: `adapter-mainline-stubs-u16t1.jar` (284 classes, this dir; NOT in landing-paths —
artifacts ship via the generation bundle, cx-bms bakes the boot image at U16 assembly).

## The 8 methods (from stub_member_gap, com.vrem.wifianalyzer_72.apk.282a06fc pre-patch)

Exactly the dispatch list, verified against the gap output (not from memory). Signatures
mirrored from AOSP android-14.0.0_r1 WifiManager (the donor file the 2026-10-02
android-net-stub-members work cites; that donor copy kept verbatim on master for cross-check).
Semantics = "no Wi-Fi device": `getScanResults` → empty list; `getConnectionInfo` → default
WifiInfo; `isWifiEnabled` → **false** (outer 11:45 overrode the old donor's true); all other
booleans → false; **no method throws**.

## Build (landed pipeline, tee'd to build.log)

`android-net-stub-members/build_patch.sh` on the U15 base → "merged 138 member(s) into 17
deployed class(es); 8 new class(es); 0 error(s)". Receipt beside the jar.

## Reproducibility — FIXED per outer 11:57 (byte-identical jars)

The first build's jar bytes differed per run (smali's run-dependent item layout + zip mtime).
`build-deterministic.sh` (this dir) is the outer's recipe, verified:

1. `build_patch.sh` -> merged smali tree (content-identical every build, unchanged).
2. **`smali assemble --jobs 1 -a 29`** — single-threaded assemble kills the run-dependent
   type_list/annotation layout; classes.dex is byte-identical across passes. (Needs
   jcommander 1.64 on the CP: 1.78's PositiveInteger annotation crashes on JDK 21.)
3. **Repack onto a copy of the BASE jar via python zipfile**: entries keep the base's
   compression; classes.dex replaced STORED; **every timestamp pinned to 1980-01-01**
   (`zip -X` alone still stamps mtime — that was the last 1-entry diff).

GATE result: passes A and B -> **jar byte-identical (True)**; canonical jar =
`adapter-mainline-stubs-u16t1.jar` (this dir); an independent `./build-deterministic.sh` run
reproduces it bit-for-bit (True). The old nondeterministic jar from the first pass is gone.

## Frozen / class diff (class-diff.txt, verbatim tail)

    deployed  …94a949053ec8…  (276 classes)
    candidate …c53b7bd63f93…  (284 classes)
    8 ADDED   (donor aux classes: DhcpInfo + $1, SupplicantState + $1, WifiManager inner
               MulticastLock / SuggestionConnectionStatusListener / WifiLock, ConnectivityManager$OnNetworkActiveListener)
    0 dropped, 0 reshaped (allow-reshape = Landroid/net/wifi/WifiManager only), 0 frozen class(es) broken

0 dropped / 0 reshaped per the dispatch gate; FZ frozen classes untouched. The 8 adds are the
donor's dependency classes pulled in by compiling the 8 methods' signatures — additive only,
each named in class-diff.txt.

## Files

- `donor/android/net/wifi/*.java` — WifiManager (new) + WifiInfo/ScanResult/SupplicantState/
  WifiConfiguration (copied verbatim from the 2026-10-02 donor)
- `members.tsv` — the 8 members (the merge gate refuses anything else)
- `build.log` — pipeline tee
- `class-diff.txt` — deployed_class_diff --frozen output
- `adapter-mainline-stubs-u16t1.jar` + `.receipt.json` — the artifact (not in landing-paths)
