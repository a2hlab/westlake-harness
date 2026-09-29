# Task 46: interrupted read-only core-class assessment

Task 47 superseded this assessment before its one-hour limit. No board writes,
lock, runtime rebuild, or compatibility conclusion was made for task 46.
These files retain partial observations only; they are not a complete ABI audit.

`CheckSystemClass` compares the preallocated class pointer with the class-table
lookup pointer. Its class dump labels `NumVirtualMethods()` as “vtable entries”;
that label is not an observation of the embedded vtable length. Likewise,
`objectSize` in that dump is the Class object size, not the String instance size.

The local C++ layout probe gives String class allocation size 795 for 80 vtable
slots. Both R155 and the rebuilt ART use the constant 80 in InitWithoutImage.
This does not establish semantic equivalence of all linking code.
The 782 ART entries unmatched against the provider-v12 fingerprint include
721 test entries. That fingerprint is not a source receipt for R155, so the
count cannot be treated as the number of missing runtime fixes.

The DEX inventory records declarations from B5-matching JARs. DEX declarations
do not encode physical field offsets. The C++ record layouts are compiler
observations of the reconstructed source, not measured live object layouts.
