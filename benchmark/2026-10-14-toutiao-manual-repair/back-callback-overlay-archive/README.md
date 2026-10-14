# BACK51 build archive receipt

The frozen source package reported archive persistence as pending. This independent receipt now verifies the existing local and hw248 archive: 5,254,743 bytes, SHA `c939f89722c73baca07f01a8a655e8867aa3110edf235359b4a8d7d8abd201f3`. The original frozen package is unchanged.

[Archive receipt](archive.json) and [results](results.json) verify 422 tar members, including 386 regular files hashed in [members.json](members.json). Four original build command receipts report rc=0; each original stdout and stderr matches its recorded SHA. The input JAR, candidate JAR, transformation source and all six locked dependency JARs match their expected hashes. The candidate SHA is `ae82e987b708441b3d6069ad04cb81e7846401a09fc9f34a84e854cc79783c33`.

26 frozen members are inside the archive. Three additional frozen review/spec/test references are verified against master commit `1c09e113037cfb1eb995739bb8a89ea708a3862c`; they are intentionally listed as repository dependencies rather than claimed as tar members. Java and javac binary hashes are recorded, but the JDK itself is not bundled. No build or device operation was run during this audit. Archive persistence alone does not establish successful navigation, deployment acceptance, or a seal.
