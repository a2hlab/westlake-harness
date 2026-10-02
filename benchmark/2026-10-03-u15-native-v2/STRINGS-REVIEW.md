# U15 native v2: unsigned strings review

Original stdout and hashes are retained. None of these rows is signed or applied.
Flutter has 0/0 selected readonly-string changes under the production tool; ATrace +3 exports and +3 direct runtime imports are checked separately.

| Object | Action | Exact public-view string | Source | Proposed reason |
|---|---|---|---|---|
| runtime | DROPPED | `.......n..U...S...9....]..>Q...^..6&#124;..G...+...w.......St12length_error` | `inputs/source/egl.cpp:41` | Printable non-text fragment shifts with code/readonly layout. Do not infer semantic equivalence from strings; outer binary review required. |
| runtime | DROPPED | `ANativeWindow_fromSurface` | `inputs/source/egl.cpp:41` | Converter dlsym name becomes a direct same-image reference; export is retained in ABI/dynsym. |
| runtime | DROPPED | `[ 1c73e] row ` | `inputs/source/egl.cpp:41` | Debug producer row address shifts with the changed object; not a runtime message. Proposed review only. |
| runtime | DROPPED | `[WL-OPENGL] ANativeWindow_fromSurface not found.` | `inputs/source/egl.cpp:53` | Direct non-null function address eliminates old dynamic-lookup-miss diagnostic; no failed lookup fallback is added. |
| runtime | ADDED | `......Mn..U............]..eQ...^..` | `inputs/source/egl.cpp:41` | Printable non-text fragment shifts with code/readonly layout. Do not infer semantic equivalence from strings; outer binary review required. |
| runtime | ADDED | `EGLImpl window surface: converter=%{public}p surface=%{public}p anw=%{public}p oh=%{public}p` | `inputs/source/egl.cpp:60` | New HiLogPrint diagnostic for GL-thread Java Surface to ANativeWindow/OH conversion. |
| runtime | ADDED | `WL-OPENGL` | `inputs/source/egl.cpp:60` | New HiLogPrint diagnostic for GL-thread Java Surface to ANativeWindow/OH conversion. |
| runtime | ADDED | `[ 1c750] row ` | `inputs/source/egl.cpp:41` | Debug producer row address shifts with the changed object; not a runtime message. Proposed review only. |
| runtime | ADDED | `&#124;..G.......w.......St12length_error` | `inputs/source/egl.cpp:41` | Printable non-text fragment shifts with code/readonly layout. Do not infer semantic equivalence from strings; outer binary review required. |
| host | DROPPED | `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/.artifacts/candidate-stock-host.patched.c` | `inputs/source/n4-host.c:1` | Same resident-compat code, build-time source location changes in __FILE__/debug literal; public view is portable, raw literal hash retained. |
| host | DROPPED | `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-03-u14-appns-build/inputs/resident-compat.h` | `inputs/source/u10-1-resident-compat.h:1` | Same resident-compat code, build-time source location changes in __FILE__/debug literal; public view is portable, raw literal hash retained. |
| host | DROPPED | `SL_IID_BUFFERQUEUE` | `inputs/source/n4-host.c:362` | Mindustry owner validation uses Android simple-buffer-queue IID instead of unsupported old buffer-queue IID. |
| host | DROPPED | `{.......{.......{...r....` | `inputs/source/n4-host.c:123` | Address/table printable fragment changed with the extra package literal and layout; outer binary review required, not automatic allow. |
| host | ADDED | `$WORKSPACES/westlake-harness-t3/benchmark/2026-10-03-u15-jitsi-native-domain/.artifacts/u15jitsi-stock-host.c` | `inputs/source/n4-host.c:1` | Same resident-compat code, build-time source location changes in __FILE__/debug literal; public view is portable, raw literal hash retained. |
| host | ADDED | `$WORKSPACES/westlake-harness-t3/benchmark/2026-10-03-u15-jitsi-native-domain/inputs/resident-compat.h` | `inputs/source/u10-1-resident-compat.h:1` | Same resident-compat code, build-time source location changes in __FILE__/debug literal; public view is portable, raw literal hash retained. |
| host | ADDED | `/org.jitsi.meet/` | `inputs/source/n4-host.c:290` | Meet enters matching ANL/host native-domain lists and resident runtime publication, atomically with the ANL alias pair. |
| host | ADDED | `K.......K.......K...r....` | `inputs/source/n4-host.c:123` | Address/table printable fragment changed with the extra package literal and layout; outer binary review required, not automatic allow. |
| host | ADDED | `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` | `inputs/source/n4-host.c:362` | Mindustry owner validation uses Android simple-buffer-queue IID instead of unsupported old buffer-queue IID. |
| host | ADDED | `org.jitsi.meet` | `inputs/source/n4-host.c:127` | Meet enters matching ANL/host native-domain lists and resident runtime publication, atomically with the ANL alias pair. |
| anl | ADDED | `org.jitsi.meet` | `inputs/source/u15-app-native-loader.c:66` | Matching Meet native-domain package whitelist; must ship with host and both identical ANL aliases. |
