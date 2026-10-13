# Boat R4: geometry, cadence and source-derived controls

The earlier recipe omitted the historical geometry fix at **libandroid.so**.
Mapping runtime `94718e0d` alone left the R3 display stretched. R4 retained that
runtime and added the exact `9ccf64f8 -> adc125f4` libandroid replacement. The
controlled W3 boot then displayed round controls and a correctly proportioned
1920×1200 scene. ADC must not replace runtime `18763dd4`/`94718e0d`: that would
remove unrelated runtime APIs. The path distinction was the missing recipe item.

The ADC reproduction changes exactly **49 bytes** from the archived 9cc input:
47 executable bytes in four geometry functions and two class-name bytes. The
preserved new replay returned rc=0 and reproduced the complete ADC SHA. This is
a new byte replay, **not the missing historical ADC build log**. Historical
source/build reproducibility remains unclosed; the discovered `0d7b` runtime
build log must not be attributed to ADC. See [closure](evidence/adc-closure.json),
[patch sequence](evidence/adc-patch-sequence.json) and
[raw replay output](evidence/adc-replay.stdout.json).

## Visual and input result

The independent [t2b visual verdict](../r4-interaction-review/t2b-visual-verdict.json)
is **PASS for the Boat visual/touch scenario**, with user-authorized,
source-derived coordinate supplementation. Ten-control regression and final V2
sealing are separate and pending. No acceptance gate was added or weakened.
The original incomplete verdicts remain unchanged.

All accepted interactions used boot `35da6f13-e7b1-4472-a36a-5c4a69d5f191`, child
`10322/birth72028`, parent `4516/birth7361`, UID `20011062`. The existing per-step
identity guards completed and the actual child-root raw receipts matched all
seven candidate file hashes. These are host-side reviews of outer-collected
evidence, not new device commands.

| Evidence | Observation |
| --- | --- |
| [Historical ready](evidence/historical-ready.jpeg), [R4 t30](evidence/t30.jpeg) | Round controls, compact HUD, correct scene proportions; no earlier horizontal stretch |
| [Original first accelerator](evidence/original-touch1.jpeg) | TIME 00:28.225, LAP 1/3, lap timer 00:10.561; boat reaches rock |
| [Original left](evidence/original-left.jpeg) | TIME 00:39.784; bow/near-rock orientation changes after left input |
| [Reset before](evidence/reset-before.jpeg), [after](evidence/reset-after.jpeg) | Existing control moves the same boat out of the rock onto open course water |
| [Right before](evidence/right-before.jpeg), [after](evidence/right-after.jpeg) | TIME 11:47.776 → 12:00.369; heading changes from docks/yellow boats toward open sea between fixed rock columns |

The right verdict uses fixed shoreline/rock landmarks and the recorded positive
steering command; wave animation and other boats' motion are not steering proof.
Reset is supplementary escape evidence, not a new mandatory specification gate.
KPH two-digit speed is not required by the original specification.

## Why the first two interaction runs were inconclusive

The historical script waits for a populated surface queue and verified geometry,
then sleeps **3 + 6 + 6 + 15 seconds**, with intervening captures/checks. It next
runs the original five commands with after-images; only reset has an extra
two-second wait. R4's initial two-stage procedure added t45, cleanup, human
handoff, repeated seven-pin checks and before-images. A shorter two-stage run
still started too late. Neither failed LAP observation is discarded.

The final `original-cadence` runner kept initial seven pins, identity and window
geometry checks, captured t15/t30, and immediately ran the original five
commands. It deferred cleanup until afterwards. Actual HUD time, rather than
the label t30, establishes the comparison: current first-touch TIME **00:28.225**
versus historical **00:25.354**, a 2.871-second difference. Current LAP progressed
from **0/3 to 1/3**, matching the historical progression and collision state.
This supports cadence sensitivity; it does not prove delay was the sole cause.
No further repetition of the same recipe was proposed.

## Existing controls and exact parameter derivation

The original [touch prefab](sources/Race_Canvas_touch.prefab) inherits constant
Canvas scale **0.7** from [Race_Canvas](sources/Race_Canvas.prefab). For the current
1920×1200 frame:

| Control | Center, top-left pixel coordinates | Hit rectangle | Existing binding |
| --- | --- | --- | --- |
| Steer | 154,1046 | x84–224, y976–1116 | Gamepad leftStick → Steering → Engine.Turn |
| Reset | 1584,1074 | x1514–1654, y1004–1144 | Gamepad select → ResetBoat → ResetPosition |
| Accelerate | 1794,1074 | x1724–1864, y1004–1144 | Gamepad buttonSouth → Trottle → Engine.Accelerate |

There is no brake among the two right-hand circles. Reset's center is
`(1920-(380+100)*0.7, 1200-(80+100)*0.7)`. The old reset `(1440,1100)` is
74 pixels left of its hit rectangle. Original steering start `(220,1000)` is
inside the rectangle, only four pixels from its right edge; being outside the
drawn circle alone does not establish a miss. The local Unity Image default
alpha hit threshold is zero (rectangular hit testing).

[OnScreenStick](sources/OnScreenStick.cs) stores the pointer-down position and
sends `(current-down)/150`, clamped to unit magnitude. Thus 150 local units are
105 screen pixels. `OnPointerUp` sends zero. The authorized parameter derivatives
used existing controls, without changing runtime bytes:

```text
reset: uinput -T -c 1584 1074 200
right: uinput -T -m 154 1046 259 1046 -k 5000 700
left counterpart: uinput -T -m 154 1046 49 1046 -k 5000 700
```

The left counterpart is a source-derived parameter, not a claim of an additional
executed command. The accepted left evidence is the original-cadence sequence.
[HumanController](sources/HumanController.cs) and [Engine](sources/Engine.cs)
confirm positive steering means right. [Boat.ResetPosition](sources/Boat.cs)
uses the nearest waypoint, clears linear/angular velocity and sets course
rotation; it does not restart the process or clear the race.

Full source hashes and generated IL2CPP locations are in
[control-hit-map](../r4-interaction-review/control-hit-map.json) and
[source/reset review](../r4-interaction-review/source-reset-and-steer.json).
These source mappings do not claim a new complete APK build reproduction.

## Raw evidence archive handoff

[archive/index.json](archive/index.json) declares a point-in-time inventory of
all W3 regular files except generated Python cache. Every raw command receipt,
earlier inconclusive attempt, plan, apply/preboot/boot trace, capture, hilog and
existing close evidence is retained. Manifest TSV columns are SHA256, bytes,
relative path. Paired `.paths.txt` files are exact tar inputs. No large runtime
binary or raw hilog was copied into this landing package; no original was removed.

Before outer creates the archive, verify this inventory and emit one tar list:

```sh
python3 "$CLOSURE/verify_archive_inputs.py" --root "$W3" --out-list "$TMPDIR/boat-w3-archive.paths"
tar -C "$W3" -cf "$ARCHIVE" -T "$TMPDIR/boat-w3-archive.paths"
shasum -a 256 "$ARCHIVE"
```

`CLOSURE` is this directory; `W3` is the root declared in archive/index.json.
`ARCHIVE` is an outer-selected local destination. The verifier rejects changed
or missing declared files and reports later additions; additions need a separate
supplement if they are to be archived. It never writes W3 or invokes a device or
network command. Runtime CAS dependencies remain pinned references, not falsely
claimed members of this raw archive. Remote path/SHA/verification receipt remain
pending until root archives to hw248 and independently checks its bytes.

Outer reported W3 closed and unlocked at 12:17 after exact-UID cold_stop. Later
10-control prelock table drift (`expected d70e…`, `actual 2e389…`) is owned by
BMS/T0 and is not resolved or excused by this knowledge package.
