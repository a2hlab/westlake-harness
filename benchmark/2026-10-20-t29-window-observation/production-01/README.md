# T29 joint offline production 01

Both exact baseline ELF relinks reproduced their original bytes. All 22 actual
commands returned rc0. The new bridge was linked first; its three owner function
addresses and two reference GOT slots were then extracted and used only in new
pair/geometry source copies before compiling the paired shim.

Bridge export/version tuples (2089), shim tuples (78), and both dependency lists
are unchanged. The actual ELF JNI tables retain 12 SurfaceTexture and 4
TextureView name/signature/function-symbol identities. Runtime binding remains
UNKNOWN; this is not deployment admission or a playback result.

**Outstanding admission review:** both original consumer translation units
recompiled to objects with different SHA values from their historical objects.
`consumer-original-object-comparison.json` records both pairs. No semantic
equivalence is claimed. The exact baseline relinks reused historical objects;
that success does not close the source-to-object difference.

Original argv/stdout/stderr/rc and ELF/object bytes are retained under
`../.private/production-01/`; the top-level launch is in
`../.private/production-01-launch/`. `raw-index.json` pins every original file,
including the unmodified private receipt. `receipt.public.json` only replaces
path prefixes with $T4/$MAIN/$CC/$BRIDGE_INPUTS/$HOME aliases.
The accepted checkpoint02 and historical failed preparation evidence were not
modified. No compiler failure occurred in this production attempt.
