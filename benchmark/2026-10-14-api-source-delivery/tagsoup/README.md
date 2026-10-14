# FZ-007 / REG007 source delivery on master

The former default-branch TagSoup parser was an incomplete stub. The frozen full implementation was referenced by a branch-only Parser and a15-file SHA list, which did not deliver a complete rebuildable implementation. The new [source directory](../../../sources/api-implementations/FZ-007-tagsoup/README.md) contains all15 exact frozen Java files, original license metadata, an executable component/full-T7d build and locked dependency retrieval.

- Exact frozen matches:15/15; Parser SHA `aa68cc4d04869aee423b799eb990237301cf40d2f59b77c47549a88e32b38425`.
- Full original T7d composition:125 concrete repository sources =103 existing master files +15 TagSoup +7 exact historical overrides. Every source has a direct repository path and SHA in the [source lock](../../../sources/api-implementations/FZ-007-tagsoup/t7d-sources.lock.json).
- New component build and malformed-HTML/XMLReader/entity/SAX check:PASS,16 class files.
- New full T7d build:javac rc0,205 class files; D8 rc0. `classes.dex` `deeb2a2157087d4367cafd6f30878c8f22a2e2089da4b304368b95b7b7bf6860` equals the historical production dex byte for byte. ZIP jar-wrapper bytes differ and no new deployment is claimed.
- Dependency retrieval replay:all5 pinned jars extracted and verified from the durable bundle.

The original final javac/D8 stderr and source list are preserved separately from the new2026-10-14 raw command logs. Complete original stdout/exit receipts remain unlocated. The earlier `t7d-dockbuild.log` belongs to a different jar and is not used as production build proof. This distinction remains explicit in [results.json](results.json).

Durable raw dependency/source/build bundle: `hw248:/home/alvin/westlake-tagsoup-t7d-source-delivery-20261014T120200-6195ef3c/tagsoup-t7d-build-evidence.tar.gz`; SHA `1601909ba759a1f3dd7275a20db6b803e85087e3b030fc3280f9a176a07d7ed5`; 73,822,945 bytes. All390 source/evidence files, front/back metadata/SHA, exact tar members, remote SHA/size and gzip passed. The bundle includes a125-source snapshot, all5 binary dependencies, original residual logs and both new builds. The public repository contains the implementation code and executable recipes; large jars and raw logs remain in the bundle.

[delivery-files.json](delivery-files.json) is the exact handoff list. This lane did not modify old frozen files, devices or the original315-row view and did not stage/commit/push. Root owns the final master commit and source-table integration.
