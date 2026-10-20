# Exact 85c789 WebView shim closure lead

The current shim source resembled the deployed ANativeWindow stubs but did not establish whole-library provenance. A bounded filename search found the exact deployed 51,816-byte library in `$ORB_WS/out-npthrefuse49`, plus its two original objects. The C object is `00634817…`; the assembly object is `de6a8a23…`. All hashes were read from actual files. No rebuild or device call was performed.

The historical #49 README explicitly associates this artifact with Westlake commit `b14e4d08…`. Reading that Git object yields `framework/webview-shim/webview_bionic_shim.c`, 79,148 bytes, SHA `45f0b40c…`. This is a specific historical binding, not a fresh compilation proof. It differs from the later current source used in the initial comparison.

The original #49 folder has no compile/link receipt. Earlier `out-sp20/webview-shims/artifacts.json` and `out-ability38/webview-gles-order/build.json` preserve same-family compile/link recipes and the exact existing map/assembly/CRT input paths. Their historical outputs are ae6ac828/ecc7b12, respectively, so they must not be relabeled as #49 records. The smallest next step is an untouched relink of the original #49 objects in a new output directory, requiring exact85c789 before source recompilation or a narrow ANW change. This lead was passed directly to video_plan; no additional runtime library or preload is proposed here.

`results.json` records exact source/input hashes, recipe limits and remaining gaps. `$ORB_WS` means the mounted original build-workspace root supplied by the operator, not a hard-coded personal path.
