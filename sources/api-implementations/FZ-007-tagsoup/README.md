# FZ-007 / REG007: complete frozen TagSoup source

The default branch previously contained an incomplete two-file stub, while the frozen production parser was only referenced by another branch and a15-file hash list. This directory now carries all15 exact production TagSoup Java files, the original upstream license, a repository-only125-source T7d composition and executable offline build entry. No frozen runtime file or deployed artifact is changed.

- **Implementation:** [`src/org/ccil/cowan/tagsoup/Parser.java`](src/org/ccil/cowan/tagsoup/Parser.java), with all15 siblings enumerated in [`FROZEN-SHA256SUMS.txt`](FROZEN-SHA256SUMS.txt).
- **License:** original [`LICENSE`](LICENSE), original per-file notices, [`Android.bp`](Android.bp) license metadata and upstream README files are preserved.
- **Build:** [`build.py`](build.py), [`t7d-sources.lock.json`](t7d-sources.lock.json), [`dependencies.lock.json`](dependencies.lock.json), [`fetch-dependencies.py`](fetch-dependencies.py).
- **Validation:** [delivery results](../../../benchmark/2026-10-14-api-source-delivery/tagsoup/results.json) and [new full T7d build receipt](../../../benchmark/2026-10-14-api-source-delivery/tagsoup/t7d-build-receipt.json).

The15 files match every SHA in frozen commit `6b2e921203ab1489d2d88a58c740590369369cf2`, including Parser `aa68cc4d04869aee423b799eb990237301cf40d2f59b77c47549a88e32b38425`. The recovered upstream checkout was clean at AOSP external/tagsoup commit `e3878034313345558f88966c54c2e2195a514186` (android-14.0.0_r1 lineage). Four optional upstream `jaxp/` files were absent from the original frozen/T7d source set and are deliberately outside this delivered production set. The upstream Ant/Gradle/Soong files are historical metadata; use `build.py` for this exact frozen subset.

## Build the component

Python3 and a JDK are required. Set `JAVA_HOME` to select the JDK. Output directories must be new.

```sh
python3 sources/api-implementations/FZ-007-tagsoup/build.py --out /tmp/tagsoup-component-new
```

This compiles the15 files and runs a real XMLReader assignment plus malformed-HTML repair, entity decoding and SAX-callback check. It writes raw stdout/stderr and per-command exit/SHA receipts. The verified component run used Java8; its standalone classes jar is a test artifact, not the Android boot-classpath package.

## Rebuild the exact T7d source composition

All125 Java inputs resolve to real files on this default-branch tree:103 unchanged existing `bms/` files, the15 TagSoup files here and7 exact historical overrides in [`t7d-overrides/java/`](t7d-overrides/java/). The source lock checks each SHA and refuses drift. None is resolved through another branch, worktree, OrbStack path or build server. The overrides are historical inputs, not modifications to current frozen runtime files.

The four compile-only jars and R8 are binary dependencies, kept in a verified durable bundle rather than Git. Obtain them through the project's configured `hw248` SSH alias, or supply a previously downloaded bundle with `--archive-file`. The download and every extracted member are SHA/size checked; only the five locked dependencies are extracted.

```sh
python3 sources/api-implementations/FZ-007-tagsoup/fetch-dependencies.py --out /tmp/tagsoup-deps-new
python3 sources/api-implementations/FZ-007-tagsoup/build.py --mode t7d \
  --dependencies /tmp/tagsoup-deps-new --out /tmp/t7d-rebuild-new
```

Use JDK17 for the full build. The executed verification used OpenJDK17.0.20.1 in local amd64 image `a2hlab-b5-java:24.04`, image ID `sha256:f39400369f20f4ba610693834f148581376d05c2f321e6194d5bd2934fece4c1`. The recipe runs javac with the original four-jar classpath, then pinned R8 D8 with `--min-api 34`. All125 inputs compiled to205 class files; D8 rc0 produced `classes.dex` SHA `deeb2a2157087d4367cafd6f30878c8f22a2e2089da4b304368b95b7b7bf6860`, byte-identical to the historical production T7d dex. The new jar ZIP wrapper differs from the historical `d8b2406e…` jar; it is not claimed as a byte-identical deployable package. No boot image was rebuilt or deployed.

## Historical versus new logs

Original `javac-t7d.err`, empty `d8-t7d.err` and `srcs.txt` survived in the exact original T7d build workspace; their raw bytes and SHA are retained in the durable bundle. The complete historical javac/D8 stdout and final command exit receipt have not been located. The old `t7d-dockbuild.log` belongs to earlier jar `6e2f450e…`, so it cannot prove the final full-TagSoup `d8b2406e…` build. Existing `t7d-build-receipt.json` explicitly describes a retrospective inventory and unknown original image log.

The2026-10-14 rebuild has new, separately labelled stdout/stderr, command exits, source/dependency hashes and output pins. It reproduces the historical dex; it does not recover or rewrite missing historical execution logs. [`dependency-bundle.lock.json`](dependency-bundle.lock.json) pins the durable dependency/source/log bundle, while the public report keeps portable paths and small receipts.
