# Actual owner review: missing libandroid repair, not a runtime incompatibility

## Confirmed

Boot cfdccb61, child5058/birth307730, parent5049, UID20011062. Actual child-root
hashes are **libandroid9cc** and **runtime947**. The six-pin gate did not cover
libandroid. The historical PASS recipe requires **adc at both paths**; the
libandroid half of that historical geometry repair is missing from this run.

Fresh local ELF comparison **9cc->adc**: both744856 bytes,49 changed bytes
(47 executable +2 class-name bytes),**268/268 exports**,0 added/removed,
all symbol metadata identical and0 undefined-symbol delta. The4 geometry
changes are the already-reviewed original fix, not a new implementation.

The SQLite weak registrars and520 missing U13 exports were diagnosed for
**adc replacing full runtime187**. They are not new in adc relative to9cc and
do not justify a blanket prohibition on its historical **libandroid** role.
Keep the complete runtime947 and its real JNI registrars; never replace it
with adc. Original successful whole-generation replacement is not proposed.

## Actual binding is not yet observed

Maps show **two loaded9cc instances** and **two947 instances**, with the same
file inode within each pair but different bases. Both ELF SONAMEs are
`liboh_android_runtime.so`. Unity requires `libandroid.so` and has real
JUMP_SLOT imports: fromSurface at0x172dac8, setBuffersGeometry at0x172d898.
These facts make the old9cc owner a concrete explanation, but **do not prove
the resolved GOT values or linker namespace membership**. Linux mount views
and linker namespaces must not be conflated. The JSON supplies each possible
function address for an existing readonly owner probe; ASLR/PID changes invalidate
those addresses, so they are tied strictly to the captured boot/PID/maps.

Both owner-readonly/hilog and interaction/hilog-final contain only
`Mutlti commands can't be used in combination [CODE: -31]`. There is no usable
geometry call trace in those files. The current strict HUD rejection is taken
from the outer run, not inferred from this failed log capture.

## Minimal historical reuse and T4 handoff

Reuse exact **adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130**
only at `/system/android/lib64/libandroid.so`, with exact9cc preimage rollback.
Retain runtime947, adapter8ab, JAR633 and the3 existing private files. This is
an **offline candidate recommendation**, not a claim that the mixed947+adc
recipe has passed a board run or that duplicate-owner routing is repaired.

T4's7-bind r4 chain must bind the additional exact source, checksum it, protect
the actual preimage, use the same namespace/activation ordering, and expand
the child-view check to **7 pins**. Worker source/table/receipt/plan and rollback
must agree on7; no silent old BOUND6. Do not alter the preserved runtime target,
inflate full319 expected membership, or borrow v1 Plan2 current20 instead of
the128 shared-change gate. Actual source paths/pins and this control delta are
the next narrow review; no installer redesign, new binary or board action here.

`actual-owner-review.json` binds13 local sources and records the fresh export
check, maps lines and relocation offsets. Original89 and previous19-file
landing lists are unchanged. This addition has its own small landing list.
