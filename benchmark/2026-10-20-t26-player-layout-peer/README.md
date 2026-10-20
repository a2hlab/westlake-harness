# Exact player YV12 writer layout

The chroma height is **ceil**, not floor. The player consumes the returned buffer stride; it does not derive that stride by aligning the requested width.

For positive, nonoverflow dimensions, exact player `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`, helper ELF `0x1fa3e4` uses `YS=buffer.stride`, `CS=alignup(floor(YS/2),16)`, `CH=ceil(buffer.height/2)`, `V=bits+YS*buffer.height`, and `U=V+CS*CH`. See results.json for precise PCs and the format-selection chain. writer-instructions.txt is the verbatim instruction-only excerpt of the pinned raw output.

If the adapter returns `YS=alignup(W,16)`, its proposed `CS=alignup(ceil(W/2),16)` is algebraically equivalent for positive nonoverflow W. This does not establish general odd-size allocation, crop, conversion or optimized-path correctness. Restricting admission to the observed even sizes is sufficient for this scoped review.

The existing full REA was reused without a new REA call. A bounded local llvm-objdump command completed with rc0. Its exact original argv/stdout/stderr/rc and SHA references are preserved in results.json under the durable private evidence directory. No device operation or build occurred.
