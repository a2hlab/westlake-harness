# T34 W03 follow-up archive: remotely verified

After root confirmed both windows closed/unlocked and froze their directories, the reviewed repository [producer](../archive-03-preparation/archive.py) ran once and returned **0**. New archive `HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/window-03.tar.gz` is **1,163,052 bytes**, SHA256 `6ce781199f13de7960973db5899df0e7b1b1b1afd2abaf29cb9045619bfb3f02`. All **4,746 payload files** matched remotely; the tar contains one additional `MEMBERS.json` entry.

The reservation, upload, no-clobber publication and full remote verification commands each returned0. The remote script checks compressed hash/size, exact member set/count and every payload SHA/size. Independent local replay reopened the actual archive and checked all 4,746 payloads against both embedded and separate manifests. [Results](results.json) pin the private command receipts, producer, closure confirmation and critical members without exposing raw command bodies or accounts.

Source counts: W-03 **747**, W-03-b **3939**, network readiness **60**. Collector per-file stat checks and the final inventory comparison passed; there was no forced retry after drift. Exact outer stdout/stderr/rc remain at the aliased private execution directory recorded in results.

The [earlier W01/W02 archive](../archive-01/README.md) remains unchanged (`ec5cb95d…`); the new name cannot overwrite it. Earlier baseline references retain their original ownership and may require that earlier package. Remote staging/reservation remains intentionally retained, and the published file was verified with mode0600 by the inherited verifier.

This is an integrity receipt, not a video/feed/audio or retention verdict. No device access, runtime modification or remote Git push occurred in this archive operation. Existing API rows and reports are untouched; root may append these exact public receipt references separately.
