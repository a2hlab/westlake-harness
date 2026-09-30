# Upstream trees the R155 recipe consumes (listed, NOT vendored)

`cross_compile_arm64.sh` / `gen_boot_image.sh` take two upstream source roots as args
(`--oh-root=$OH`, `--aosp-root=$A`). These are large source trees — recorded here by identity and
location rather than copied into the repo.

## OpenHarmony (`--oh-root`, `$OH`)
- **openharmony-6.1.0.31** — the route-A base OS version (matches the boards' `const.ohos.fullname`).
- Local slice: `westlake-harness-bms-deploy/bms/src/upstream/openharmony-6.1.0.31/` — top level `base/`,
  `interface/`, `third_party/` (a headers/interface slice, not the full OH checkout).
- Persistent full copy: hw248 `/opt/wl-src/upstream/openharmony-6.1.0.31/` (RUNBOOK: route-A frozen inputs).

## AOSP (`--aosp-root`, `$A`)
- **android-14.0.0_r1** ART base — `art-r1` commit `3c05e56` (the T1 patch-series base; kImageVersion=108,
  kOatVersion=230).
- Persistent build tree: hw248 `/home/alvin/aosp-14.0.0_r1-art/` (T3/T3b build tree; host dex2oat64 +
  target/host libart out there). The 21-patch series that turns art-r1 into art-hanbin/R155 source is
  vendored at `knowledge/toolchains/art-r155/{patches,series,SOURCES.md}`.

## ADAPTER_ROOT
- The vendored `adapter/` tree in this recipe dir (the scripts default `ADAPTER_ROOT` to their own
  location, per `PROVENANCE.md`).

Note: these roots are not needed to *read* the recipe (the scripts + macros are fully vendored here); they
are needed only to *re-run* a build, on hw248 where both trees already live.
