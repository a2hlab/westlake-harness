# T18 post-close full candidate log supplement

The closed T18 window archive does **not** contain this later acquisition. This separate supplement preserves the full historical candidate log read after close, all five command groups (before/after lock inspection, before/after file verification and receive), their original stdout/stderr/rc, and the original result.

The received log is 33,438,849 bytes, SHA256 `eabb6fbe6836b388a22c18bf6386f0fe4d459b379e9972aded1111d48b558802`. Before and after reads agree on device/inode/size `66352:188416:33438849` and SHA. Both verified shell reads and file receive returned 0. Both held checks returned 1 with empty stdout. The receipt binds historical candidate boot `6b99680b-3d15-476a-a229-dc3591e34add` and acquisition boot `9e75bd0f-e7cd-4819-a8e1-00c6512d020b`.

This is historical-file preservation, not a new live-player observation. No playback, provider-binding, decoder, or causality claim is added. Media URLs/tokens and the complete log remain private. Public copies of command receipts replace personal paths with aliases and retain original and public SHA values in `packet/source-index.json`.

`packet/archive-receipt.json` reports local verification; remote verification remains pending until outer's actual transfer receipts. The independent tar contains every selected original file unchanged and has been checked member by member. Original T18 tar `3d27a564111b5898882c250354f2c9dc218cf0f35490cee13d6d9a0e04522d5e`, its pending receipt and final manifest were checked unchanged.

`prepare.py` defaults to no writes. Its explicit `--write` mode creates a fresh persistent archive and public packet from existing local evidence; it never invokes HDC, a build or a network command. The three upload argv are in `.private/archive-01/remote-commands.private.json` for outer execution. Do not re-run them against an already populated destination.
