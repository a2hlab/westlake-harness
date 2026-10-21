# G01 source, generation, deployment and closure archive

Archived only after the actual G01 board UNLOCK and the outer freeze instruction. The archive includes the guardian window, r3 source/generation/test raw inputs, deployment-tool author tests and independent peer evidence. It excludes W05 and preserves all older archives.

- Remote alias: `HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/guardian-window-01.tar.gz`
- SHA256: `fe30d1d38661cd1534ad8525c18bbbced635eaeea449262444f05fccf99a0a93`
- Size:2515180 bytes;3485 payload members plus `MEMBERS.json`.
- Local archive readback and remote verification checked every payload member SHA/size. All four remote commands returned0. Unique700 reservation and600 payload, published without overwriting an existing destination.
- `members.json` lists archive-relative source aliases; `remote-success.json` records actual verification. Raw transport argv/stdout/stderr/rc and private paths remain private. The26-row raw index was replayed from its own declared root.

`archive.py` is the narrow successor of the W04 archive tool, changing only source roots, unique output name and G01 retained/UNLOCK closure validation. No device command exists in this archive flow. Source file identity is checked before and after packing, then both local and remote member verification run. The actual signed retain remains unchanged; a separate derived closure index records the absence of an original close.json honestly.

Scope remains guardian-only retained/feed verified; natural-exit reentry NOT_OBSERVED and video NOT_SEALED. See [the actual window report](../guardian-window-01-public/README.md).
