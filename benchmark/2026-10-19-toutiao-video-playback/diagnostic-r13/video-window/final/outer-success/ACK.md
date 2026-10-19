# ACK r13-video-window-final-ready — outer archive closure

Outer executed the exact three prepared argv arrays, each rc0 with empty stderr. The remote readback matches SHA256 `e1715e482873265b662efe723ee9960a2b003fb531c547de56e95933ba2ac59f`, 1,101,528 bytes; the archive has 5,124 locally validated members, independently revalidated by the outer per its handoff. Public command/stdout copies replace only declared personal/remote path prefixes. Raw-to-public hashes bind every original and sidecar. Receipt/rc/empty streams retain original bytes.

The original lane rc255 receipt, failure excerpt, raw archive and member manifest remain unchanged. This sidecar supersedes their pending remote status without erasing the failed attempt. No tar was rebuilt or uploaded by this lane.

The outer reported invoking the former `review_final.py --help`, which regenerated local review JSON. The previous script did not parse arguments. The corrected script now defaults to no writes (and explicitly reports no review performed), supports argparse help, rejects unknown arguments with rc2, and requires `--write` for regeneration. Explicit regeneration validates the outer archive receipt and preserves VERIFIED instead of downgrading it to pending.

Four actual CLI checks passed: default/help/unknown caused no file changes; explicit --write changed only results.json and retained validated remote success. Both script and results have new SHA pins. The prior script bytes are retained as `review_final.before.py.txt`; all prior51 file pins, original manifests and SHA lists remain historical evidence. Use the new complete manifest/SHA list for current bytes; historical SHA lists intentionally describe the earlier tool/results revision.

Final evidence status is unchanged: RUNTIME_RESTORED_UI_NOT_RESTORED_NO_ATTACH_NO_SAMPLES. UI was host, tracer unknown, samples0; no playback PASS. No device/MAIN calls or push occurred.
