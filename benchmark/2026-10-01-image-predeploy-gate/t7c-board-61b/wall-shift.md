# T7c on 61b: did the six target walls move? (outer check, 2026-10-01 02:35)

The lane report judged T7c by the four controls. The dispatch criterion for the six target apps was
"the NoSuchMethod/NoSuchField in hilog is gone". This table counts it.

- U5 side: each key's hilog in the U5 three-board sweep, `westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep/runs/`
  (RUNTIME 73ecf422dba2, BOOTIMAGE 0876029078e2).
- T7c side: `westlake-harness-wiki/benchmark/2026-09-30-dex2oat-l2/runs/t6-61b…-20261001T021447/batch/t6/`
  (RUNTIME 73ecf422dba2, BOOTIMAGE f25f230f5c77).

The runtime fingerprint is the same. The boot image and the stubs jar are one variable (G1 binds them).
The U5 rows come from three boards; the errors are class-content lookups, so the board does not change them.

| key | U5: first NoSuchMethod/NoSuchField | T7c: same error | T7c: next error seen | t20 (outer read) |
|---|---|---|---|---|
| wikipedia | `tagsoup.Parser.setProperty` x4 | 0 | `android.net.ssl.SSLSockets` NoClassDefFound (also on U5) | desktop |
| fd-libretube | `tagsoup.Parser.setProperty` x3 | 0 | none in hilog, process gone | desktop |
| fd-feeder | `NetworkRequest.getNetworkSpecifier` x3 | 0 | `kotlinx.coroutines.CoroutineStart` CNF (also on U5) | desktop |
| fd-gallery | NoSuchField `MediaStore$Images$Media.EXTERNAL_CONTENT_URI` x3 | 0 | `MediaStore.canManageMedia`, `MediaStore$Files.getContentUri` | desktop (alive) |
| fd-plus | `NetworkInfo.getState` x1 | 0 | `ColorMatrix.setSaturation` | desktop |
| x | `NetworkCapabilities.getLinkUpstreamBandwidthKbps` x1 | 0 | `NetworkCapabilities.getSignalStrength` | desktop |

Result: all six walls pass at log level; none of the six is lit at t20.
The controls (HelloWorld, ZigZag, aegis, ooniprobe) show their own UI at t20 on the T7c image: 4/4.

Contact sheet (not committed): the scratch contact sheet of the ten t20 shots.
Tile order: HelloWorld, ZigZag, aegis, fd-feeder, fd-gallery, fd-libretube, fd-plus, ooniprobe, wikipedia, x.
