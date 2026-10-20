# T26/T27 joint production archive

The previous state had a locally verified candidate and durable local logs but no confirmed remote archive for the joint build. This record closes that archival gap only. It does not approve deployment or claim video playback.

The unchanged candidate is SHA256 `fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9`, 96,680 bytes. The private archive is `HW248_ARTIFACT_ROOT/t26-t27-joint-production-20261020-fc58cec5/production.tar.gz`, **69,494,594 bytes**, SHA256 **`5d16542a056fca0b2ac102743b1669236de4b4670f35c88924e81247c80ed515`**.

All 116 actual production02 receipt inputs were checked against local bytes before packing. The package includes their exact content-addressed bytes (including compiler/linker/read tools, link inputs and headers), the full benchmark evidence directory, complete source snapshots, frozen public landing files, candidate/baseline outputs, original argv/stdout/stderr/rc, host/selector/ABI records and the incomplete production01. The additional `full-source-snapshot` created after the producer raw index was explicitly included. Original path-to-input mappings stay private. No older archive is required merely to recover these 116 input bytes.

The remote directory was verified absent, created without overwrite, and checked mode700; archive mode600 was checked. All three transfer commands returned0. Local and remote checks read back all **1,793 members**, exact archive hash/size, unique membership and every member hash/size. Nothing was extracted or executed. `archive-preparation.json` preserves the earlier pending state; `remote-success.json` adds the actual upload outcome. Public source references are separate from private transfer envelopes.

The archive preserves original failure and UNKNOWN records; it does not rewrite them as successful tests. Current on-device identity, metadata getter binding, image import and playback remain governed by the separate experimental window.
