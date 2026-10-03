# ANL dual-alias observer calibration

**Not a mechanical relink.** U14 eebd62f2→U15 b96a8991 adds `org.jitsi.meet` to native_cluster_path; ANL_Dlopen uses this result to select westlake_native. Fresh strings: exactly one ADDED, no dropped. Fresh disassembly: package-bound comparisons x28/x24 #0xc→#0xd (13→14); the callback-indirect scanner's zero opens is not proof of zero loader behavior.

- Actual artifact: `libapp_native_loader.so`, root and route aliases, both b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc.
- Source/patch commit: a559672a65b2e719a85eb7cc3760e875f9935fe5; `src/anl/app_native_loader.c:66`, `src/anl/app_native_loader-vs-n3.diff`, and paired `src/host-u15-vs-jitsi.diff` in u15-jitsi-native-domain. All committed source snapshots match git blobs.
- Host final source is the recipe-produced persistent u15jitsi-stock-host.c, not its unpatched input. Host9e3ad72e adds the same package and needs_runtime publication; **both host and ANL ship/rollback together**. westlake_native ABI f8619ad5 supplies the missing LIBC imports.

## First-fatal calibration

Current `u16-wall-clusters/clusters.csv`: 19 clusters, **0 rows / 0 keys covering fd-meet or meet**. Neither key appears in the four selected U13 outer signoffs. Absence does not prove lit: current first-fatal is unknown, current matrix-covered moves=0 and measured moves=0. Do not borrow cluster A's four Flutter movers to observe a Jitsi-only change.

Historical fd-meet eligibility is **1 conditional move**, not a current U16 measured mover: window5 public Hermes/React Native atfork failures at hilog25374/25376, fallback libc++ abort import25507, main terminal25527. Paired route+global ABI is expected to clear both public and fallback relocations. Next RN/Hermes/WebRTC/owner wall unknown; no lit prediction. Donor replay has 12/13 zero missing imports; libjsctooling requires missing libjsc and is not startup Hermes evidence.

## Existing现场 markers

There is **no new ANL-specific route marker**. Paired host emits:

- `[N2-OWNER]` in final source SHA `63e2d25a6c383cd886b57b3b0220da03b6f0139bbbfba208a7165b272cc17217`: 366 `fprintf(stderr, "[N2-OWNER] %s ABI global ready; search=%s permitted=%s\n",`.
- `[N3-OWNER]` in final source SHA `63e2d25a6c383cd886b57b3b0220da03b6f0139bbbfba208a7165b272cc17217`: 300 `APPSPAWN_LOGE("[N3-OWNER] resident runtime unavailable: %{public}s", dlerror());`; 303 `APPSPAWN_LOGI("[N3-OWNER] resident runtime published for %{public}s", app_name);`.

N2's namespace label is not necessarily the package literal: require search/permitted paths containing /org.jitsi.meet/ and westlake_native plus the matching ABI global-ready event. N3 unavailable is failure, not success; published means the host publication succeeded, not that ANL b96a was loaded. Pair logs with exact loaded-ANL identity and selected ABI owner/consumer relocation evidence, then compare public/fallback first_fatal. Respect signed copy ceilings; do not substitute the upstream one-runtime wish for the accepted baseline bounds.

Recommended outer observation request: **fd-meet/org.jitsi.meet** with these conditions and historical first-fatal reference. This packet does not change a window key list, grant approval, claim a new terminal result or add a log candidate.
