# J7b complete overlay JAR producer

The original receipt enumerated 43 Java inputs but omitted eight sources that the producer actually compiled: OnlineConnectivityManager, SoftwareAndroidKeyStore, five android.net compile stubs and one keystore compile stub. This directory contains **all 51 actual Java inputs**, each tied to the original Git commit and SHA in `sources.lock.json`. Receipt-listed SHA values match exactly; the eight additional hashes are recovered from that same commit, not invented as historical receipt fields. No source lookup needs another worktree or machine.

The original producer's compile, D8, baseline disassembly, injection, assembly and postflight assertions remain intact. `producer-paths.patch.original.txt` lists the complete changes: source/report/output paths become explicit isolated paths, and the original frozen registry checker uses `--git` on this repository in addition to this wrapper's exact source SHA lock. The original `--source-root` call targeted a historical worktree layout. New receipts go only to the new output directory. The lock requires the b5 baseline and all 14 exact compile/tool input jars; extra input jars are rejected.

```sh
python3 sources/api-implementations/FZ-006/full-jar/fetch-dependencies.py --out /tmp/006-inputs-new
python3 sources/api-implementations/FZ-006/full-jar/build.py --inputs /tmp/006-inputs-new
python3 sources/api-implementations/FZ-006/full-jar/build.py --inputs /tmp/006-inputs-new --out /tmp/006-jar-new --run
```

Use Python 3.9+, Git and JDK17 (`javac` and `java` on PATH). The executed image and results are in the [delivery report](../../../../benchmark/2026-10-14-api-source-delivery/full-jar/README.md). `HW248_HOST` defaults to the configured `hw248` SSH alias; `HW248_HOME` can select the archived remote home explicitly. The fetcher supports `--archive-file` for offline use and verifies archive size/SHA plus every member SHA. Only dependencies/baseline binaries are fetched; implementation sources are here in Git. The remote archive has been read back and verified.

`--run` records raw stdout/stderr, exit status and output hash. A mismatch against the historical jar returns nonzero even if the producer's internal checks passed. An API-unit compile, successful dependency fetch, or syntax check does not count as this complete build. No device or boot-image operation is part of this entry.

This is the complete original **overlay producer**, with its pinned baseline jar as an explicit binary input. It does not claim a source rebuild of every inherited baseline class or recovery of missing original execution logs. These are new executions of exact historical source. Source copyright/license comments are preserved; see [parent license notes](../LICENSE-NOTICE.md), without assigning a new license to unmarked project files.
