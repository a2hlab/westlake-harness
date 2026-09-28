R45 dynamic roots for the D600 Route-A build, bound by
`stock_child_plugin/r45_adapter_identity.env`.

These exact bytes are the final same-project bridge/runtime artifacts mapped by the successful P0
HelloWorld device process. The bridge includes the direct `libskia_canvaskit.z.so` and `libEGL.so`
edges plus the cross-DSO SceneSession/OHNativeWindow handoff from `fix0023`; the runtime is the
corresponding P0 generation root. Their device readback, Build-IDs and first-frame process maps are
recorded under
`var/evidence/journeys/J01-first-frame-visible/developer-runs/20260805T023304Z-5ce2-run28q-gpu-access/`.

`SHA256SUMS`, the R45 identity contract and Route-A input closure must change as one cohort. The
builder verifies all three before producing a generation.
