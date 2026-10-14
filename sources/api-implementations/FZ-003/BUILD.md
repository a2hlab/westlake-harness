# Build and dependency boundary

`ADAPTER_ROOT=... AOSP_ROOT=... OH_ROOT=... AOSP_LIB_DIR=... BUILD_OUT=/new/output ./build.sh` invokes the recorded runtime recipe with ASSET_FD_SOURCE set to the exact delivered source. Restore the original input/tool variables from `build-evidence/build.sh.original.txt`; `baseline-objects.json` pins the link objects, and `runtime-recipe.sh.original.txt` enumerates source groups and dependencies. No unpinned library substitution is allowed.

The frozen source commit is `8560fd68`; blob `e47ede07fda2a9a7c3f6f41ce0fd4dcdef733f49`. The current main-tree file with the same basename under bms retains the old null/Implement-me paths, so it is not the production source for this API. The source here directly creates the Java ParcelFileDescriptor and preserves the AOSP header. Complete external source retrieval for the recorded runtime generation remains a named gap, not an invented upstream revision.
