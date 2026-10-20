# T23 incremental source and build archive

The archive `bc98710e` contains 683 individually read-back SHA/size-verified files (5,537,895 bytes). Both production attempts retain their original command argv/stdout/stderr/rc and artifacts. Production-02 is the only accepted candidate. Its exact producing source snapshot, final host cases, ABI results, consumer LLVM evidence, analysis ELFs and new dependency bytes are included.

The original T20 archive SHA `57441330fa9751085cd2f199e917a2717d14d94247d761d4509cdd1d07688b20` was itself hashed, decompressed and checked against every one of its 982 data-member hashes/sizes; its embedded manifest was separately byte-compared with the recorded manifest (983 total members). Its original input manifest was read and retained. Each of the 46 actual production-02 inputs was then hashed from disk: 41 exactly match a verified prior-archive member, and the remaining 5 are included under content-addressed `new-inputs/sha256/` entries. This is a two-archive reproduction closure, not a recipe-only claim.

Production-01's superseded platform source was recovered by reversing only the reviewed same-implementation delta and matched against its existing input receipt SHA `2705e2fe`. That restoration is explicitly labelled; it is not a claim that a source snapshot had been saved during the old compile. All other per-attempt source bytes also match their actual input receipts.

The public member index preserves member paths/SHA/size while omitting local source paths. The public dependency index uses workspace/SDK aliases. Their hashes therefore intentionally differ from the private full indexes named in `receipt.json`.

The author made no network or device call. `receipt.json` points to the private three-argv file for the outer loop: create remote directory, upload, then read remote SHA/size. Remote status is **pending** until those real replies are recorded. The original T20 remote receipt remains the authority for that prior archive. Candidate code and its hashes were not changed by this packaging task.
