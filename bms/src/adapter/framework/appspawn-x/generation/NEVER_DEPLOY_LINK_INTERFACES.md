# Link-interface objects are never deployable

The earlier evidence-only prototype under
`.work/tls-generation/{import,link-stage}` synthesized AArch64 shared objects
that exported selected OH symbols. Those files are import/link interfaces,
not OpenHarmony implementations. They must never be copied to `/system`, an
image, a package, or a deployment staging directory.

This producer does not consume those interfaces. It freezes and links the real
target `libhap_restorecon.z.so`, `libselinux.z.so`, and
`libtokensetproc_shared.z.so`, with each origin path and byte hash recorded in
`provenance.tsv`. If a future host lacks a real library, the build must stop;
adding a synthetic provider requires a separately named
`NEVER_DEPLOY_LINK_INTERFACE` input plus a verifier rule that rejects it from
the artifact/deployment closure.
