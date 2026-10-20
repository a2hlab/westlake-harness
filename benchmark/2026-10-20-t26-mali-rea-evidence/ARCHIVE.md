# Private evidence archive

The original two public REA files are copied byte for byte. The evidence describes the current restored Mali driver, not an independently captured historical T25 driver fingerprint. No runtime format, actual create binding, or successful video result is added by archival verification.

The unchanged private archive is `HW248_ARTIFACT_ROOT/t26-mali-rea-20261020-fc3d5edd/evidence.tar.gz`: **8,042,481 bytes**, SHA256 `fc3d5edd3c5c8293fb1bef5193dc0531e6ec6af819ea9021eeaa34a9ed25190a`. It contains 22 regular files and 3 directories, including the closed-source driver, two-function REA evidence bundle, snapshot, identity and LLVM records. The vendor binary and raw REA material are private, not published in Git.

Remote directory absence was checked before an atomic absent-only creation. All three upload commands returned zero; directory mode700 and archive mode600 were verified. Local and remote checks verified the complete archive, exact membership, every file size/hash and directory type without extracting or executing members. `remote-success/` contains the exact member index, verifier, sanitized command envelopes and hashes of original private envelopes.

Initial local validation assumed all tar members were files and refused the directory entries before remote operations. The corrected verifier explicitly validates both types; the original peer archive is unchanged. No device call, new analysis, build or deployment occurred here.
