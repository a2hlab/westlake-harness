# YV12 physical-target correction

The accepted successor changes only the YV12 physical request from OH11 to OH12. Scratch still reports YV12; packed destination admission is OH12/Android1 and conversion writes R,G,B,255. Other RGB request mappings stay byte-for-byte equivalent. Old design snapshots are preserved. Exact e0cb evidence and bounded unknowns are in Mali-pins.json. No old runtime source or binary was changed; no board action occurred.
