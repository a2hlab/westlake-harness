# T7d reproduction protocol (recorded before execution)

Use only frozen FZ-005 dex2oat64 ae865ddd and generator 14b1f709. Hash both tools and all nine input JARs before execution. Run the frozen generator's input check, then its compiler options in the exact argv embedded in the final T7d boot.oat. The generator's normal staging would change input path strings; do not use that rewritten command.

Create a private mount namespace. Bind the fresh output directory over the original output pathname only inside that namespace, preserving embedded argv while leaving original files intact. Remount inputs and tool trees read-only in the namespace. All compiler outputs/logs/temp files go to the fresh directory. Record host, UTC-offset timestamps, command, environment identity, return code and all 27 output hashes. Rehash originals and tools afterward.

Success requires compiler exit 0, exactly 27 files, all 27 byte-identical to the archived T7d hashes, and unchanged originals/tools. Only that result permits a new reproduction receipt and eligibility change; it does not fabricate a historical log. Any difference: classify each file using headers/embedded paths/content, retain candidate separately, do not replace T7d or update bundle eligibility, stop and report. No device access.

## Authorized R2/R3 follow-up (outer ACK95 06:50:10)

Run the unchanged frozen tools, config and R1 driver twice in separate new directories. Compare all three reproductions pairwise and each against T7d. The only permitted differing field for the proposed exception is the first 64-bit element of the identified backtrace `long[2]`, file bytes `[0x3e3b8,0x3e3c0)`. All other bytes of boot.art and all other 26 files must match. At least two reproduction values must differ; if all three agree but differ from T7d, report unknown provenance rather than nondeterminism. Any other difference stops the task. Even if this narrow test supports nondeterminism, an exception is only proposed for outer approval; no bundle promotion occurs here. Read-only source review separately answers whether runtime stack printing reads the field and whether its pointer belongs to an image ArtMethod region.
