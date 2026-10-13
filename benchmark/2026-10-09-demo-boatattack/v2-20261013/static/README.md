# V2-20261013 static candidate difference and source closure

## Evidence first / changed interpretation

Baseline is the **actual sealed v1 source map**, not an old U9 bundle or the
original assembled Boat generation. Candidate is t3 commit
`a8bb2dac4a612069695ee532f9e9d3fc2d4656cf`'s five-file stock-runtime recipe.
Window9's child readback has runtime187, adapter8ab, JAR633 and private3;
its images/report are historical rendering evidence, **not** today's v2 pass.

Fresh existing-tool results against v1 bytes:

- Adapter `84695d62 -> 8ab85446`: ABI **0 removed, 2 added, 0 drift**;
  **2 functions have changed call sets** (lifecycle orientation and child-surface
  geometry). Consumer count in this first invocation is zero, not consumer PASS.
- JAR `bbc3f530 -> 6333bcab`: **216 -> 218 classes; 0 dropped, 0 reshaped,
  2 added; 0 frozen-class conflicts**. Gate exit1 is the unapproved exact additions,
  not deletion. Class-shape equality does not prove unchanged method bodies.
- Independent local baksmali readback: **215/216 existing class files exactly
  equal**, remaining `AppSchedulerBridge` retains every existing method body and
  adds only `dispatchOnMainThread(InputEventReceiver,int,InputEvent)`. Two new
  classes are `InputEventDeviceProjection` and `$1`. `jar-body-delta.json` and
  `evidence/jar-existing-bodies.diff` retain this stronger comparison. Initial
  explicit API/jobs options hit an annotation/tool error; raw rc1 is retained.
  Default-option reread rc0 is nonempty216/218, not a zero-class pseudo-pass.
- Adapter strings exit1: **12 dropped / 16 added**, including UNITY-LANDSCAPE and
  geometry messages. Raw differences remain review items, not silently allowed.
- Adapter has **3 opens on each side**, all caller-default: Mali GLOBAL preload,
  runtime NOLOAD lookup and runtime NOW fallback. Same shape is **not** a proof
  of single runtime owner; NOLOAD fallback may create a copy in an unseen scope.
  The Mali target is unresolved by the existing scanner's ADR resolver; no scanner
  change is made here. Flags/namespace differences will be kept explicit.
- Adapter DT_NEEDED is exactly the same ordered **35 names**. Three private
  consumers were subsequently checked: **0 adapter-export consumer breaks**.
  This does not resolve their entire undefined-symbol closure. Private libraries
  have350/276/10 undefined names; those counts are import inventories, not deaths.
- Full private open-site attempt hit its local45s bound (rc124); coverage is
  explicitly **incomplete**, not “no opens”. No retry or new scanner is created.
  The finished shared/host/child scans and private NEEDED/UND attribution remain
  available; private-library dlopen reachability needs a targeted follow-up.

`shared-deltas.json` pins all **9 shared roles** against v1: **2 replacements,
7 unchanged**, all9 baseline source hashes verified. `libnativeloader`'s current
evidence path is the route-a74d1 directory, not an invented root alias. Legacy
assembled SHA56e4 JAR and adc runtime are retained only as rejected history.

## Prediction boundary

`predictions.json` separates historical root/cause evidence from current unknown
first-fatal status. Historical Boat content/touch target count is **1**. Current
v1 Boat first-fatal measurement is **absent**, so the count of confirmed current
first-fatals moved is **0**, with conditional Boat target1—not symbol references
or all128 applications. No new runtime port/rebuild is proposed: stock187 remains
unchanged, and neither adc125f4 nor94718e0d is in this recipe.

## Immediate integration/source gaps

1. The old installer requires `/system/etc/init/00_westlake_u13_recover.cfg`;
   sealed v1 removed it and uses v3 cfg/actual43491 worker. T4 must integrate into
   the current control set, not install that archived recover-v4 cfg wholesale.
2. Old overlay warns on foreign adapter/JAR/runtime SHA and continues, ignores
   chcon failures, and skips private binds when package is absent. Those are not
   current missing/mismatched-input fail-closed admission. T4 owns corrections.
3. Exact adapter8ab source/patch/object/link closure was already **not proven** in
   adapter-buildchain. An old build log for089bebe7 is not an8ab receipt. Retained
   binary + artifact readback do not satisfy reproducible-source provenance.
4. JAR633 has a retained C9-only build script and smali donor path; confirm exact
   donor/tool inputs and original rc0 build log rather than rebuild in this lane.
5. Candidate128 regression and original five-touch/LAP/image comparison remain
   pending. A static superset or four historical nonblack frames is not that gate.

## Namespace and APK boundary

Current host2a871 and childdc73 are unchanged. Fresh host/child scan has8/5 open
sites and17/2 namespace edges; existing **MULTI-NS2** and four
INHERIT-AFTER-OPEN may-path findings remain, not newly introduced Boat edges.
The child creates `westlake.sealed.child` and opens adapter/runtime there, while
host paths also target configured native domains. The candidate adapter's
runtime plain NOLOAD/NOW pair still uses caller-default. Require actual child
namespace/maps/owner evidence; identical filenames or all namespace findings
being historical do not prove the candidate's runtime is uniquely resolved.

`apk-private-baseline.json` hashes the unmodified APK and all4 original AArch64
members. Only Unity/il2cpp are replaced with C7/C4 and signal-box is added at
`/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/lib/arm64-v8a/`;
libmain and lib_burst_generated remain APK-derived, not silently replaced.
Both C7/C4 DT_NEEDED include pthread bridge and signal-box. Verify actual provider
namespace/path/version, not just that a matching library exists somewhere.

## Existing provenance, not a new build

- Runtime187's exact source/toolchain and cold-build original logs are already
  archived at the directory in main adapter-buildchain/runtime-persistence.json.
  It stays unchanged; no new runtime port or fresh build is needed here.
- Adapter8ab bytes are retained locally in t3 and historically at
  `hw248:/opt/build-runs/boatattack-runtime-source-20260813T141442Z/private-aosp-lib64/liboh_adapter_bridge.so`.
  The nearby `recover-old-bridge` original log builds089bebe7, **not8ab**.
  Target-specific source/object/link/toolchain closure remains blocked.
- JAR633's script is wiki `spare-5cd/build_boat_jar_c9only.sh`, commit
  `0624b23b86289f6d01416ed5f72e114035e8e424`. It needs original
  `SC/our/smali`, two donor `SC/boat/smali` files and five tool JARs; the recipe
  records deterministic timestamps and two passes, but recipe/report statements
  are not original rc0 stdout/stderr. Complete source-input snapshot and original
  producing log are not found in the named inspected locations. Existing tool
  readback can recover code; it is not a newly proven byte-reproduction run.
- Private C7/C4 transform recipe is games-ad1ab0a7's
  `src/tools/devices/boat-attack-apk-lightup.sh:216`, with APK raw-member hashes,
  signal rename map and exact binary operations. Do not describe these proprietary
  APK transforms as Unity source compilation. Signal-box source/map is present,
  but the exact7a931 producing compiler/log receipt is not established here.
- The v1 archive-members index covers signal-box bytes but **not8ab/633/C7/C4**.
  `archive-artifact-coverage.json` records this bounded hash lookup. Preserve
  those four existing candidate files plus source inputs/logs; no large recopy is
  performed by this lane.

**Bounded closure disposition: adapter8ab is locked for new compilation, not
automatically forbidden for exact historical reuse.** Root's rc0 HW248-02 shows
8ab was a retained2274648-byte input in the named run, while its62-TU compiler log
produced2452640-byte089bebe7. The remaining metadata/logs describe runtime work;
the two requested adapter output directories are absent. No further search is
requested. Keep the original8ab binary, current known source indexes and this
explicit target-source gap. JAR/private historical inputs remain SHA-pinned;
newly built code would require its own exact source/argv/toolchain and original
rc0 stdout+stderr, not these older reports.

The t2b contract explicitly prefers reproducing and reusing the known recipe on
a spare board before a61b upgrade. No rule here makes an additional user approval
necessary solely because an unchanged historical artifact is source-locked.
AGENTS' source/archive rule remains a provenance obligation/limitation to disclose;
it is not converted into “must freshly compile every retained historical binary”.
Any deletion/weakening of frozen behavior still needs user approval. This static
review detects no such API deletion: existing JAR methods and runtime bytes are
retained. **Spare128 nonregression, original touch/LAP/image oracle, current
controls and outer static finding review remain required**, not waived by reuse.

Authorized inner point queries timeout8s/SSHrc255; root subsequently executed
all3 requested commands rc0. `outer-source-readback.json` pins those new raw
receipts: VM's named HOME/orca paths are absent (not all VM paths), hw248 confirms
exact8ab retained at the private-aosp input path. Nearby original build.env/log
names a different recover-old-bridge output. Newly revealed metadata/input paths
were checked once through `root-read-requests-r2.json`; disposition is closed for
this named run in `outer-source-readback.json`. No further inner
sandbox retry, full-disk search, download or build. Original rejected transport
raw remains historical; **unavailable transport is not an absence result**.
Required actual child fields are in `root-readonly-needs.json`.

## Root baseline correction

Latest outer readonly evidence: 5cd319 matches v1, 5ea has exactly3 deviations
(8ab/633/adc) and is **not** a clean baseline. No adc experiment is requested.
The independent five-control review in `5ea-base-delta-review.{md,json}` accepts
only the exact4c04 apply/730342 plan delta, retaining old archive. Root reports
placement rc0/RO; newboot319 proof remains separate. A clean baseline cannot be
inferred from placement alone or borrowed from the other board.

Everything here is local-only: no board/HDC/VM/SSH/build/push. Native/JAR tool
outputs and current artifact pins are under `evidence/` and `artifact-pins.json`.
