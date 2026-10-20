# Actual parent environment comparison: no unexpected content mismatch

The actual stdout bodies, command arguments and rc were checked independently. 5cd is still T32 video generation `e562ad3e`, parent5866/b13907. 61b is **restored baseline** `ce7b78ed`, parent4992/b5694; it is not failed candidate generation38774065. Both recorded boot/parent identity brackets pass.

| Collected scope | Result |
|---|---|
| Expected private BCP JARs | 9/9 identical SHA and size; no JAR-path mappings. Actual VM order is not inferred from file availability. |
| ART/OAT/VDEX boot images | 27/27 identical SHA and size; each file device/inode matches its own board's maps before and after. |
| Mapped shared libraries | 289 on5cd,287 on61b;285 of287 common paths identical SHA/size. Every collected shared file is bound to both maps snapshots by device/inode. |
| Common-path differences | Only bridge b0e→d4fa and shim7f8→85: expected candidate versus restored original. |
| Extra5cd parent mappings | compat6e83 and system OpenSLES05d8; absent61b mapping does not mean absent physical file. |
| Media/player | Neither mffmpeg nor ttmplayer appears in either parent map. No child loading/winner conclusion. |

`diff.json` contains the four mapped differences and selected environment differences, with full hashes, sizes, local identities and stdout line references. The six environment changes are the expected owner UID/WID and candidate-versus-original native target/preload/inherit settings. No unexpected content mismatch was found in this collected scope.

Deleted memfd JIT/font mappings remain UNKNOWN. Matching maps inode and current file bytes are stronger than physical-stage equality, but do not replace child call-site/namespace evidence or retrospectively establish bytes at every earlier screenshot. In particular, this recovered61b read cannot diagnose the previous failed candidate. No difference is claimed as the cause of a crash or white screen.

Next useful action is to inspect existing W03-b candidate-generation child/parent startup and maps evidence for the first still-unproven transition. The comparison gives no reason to change the equal BCP files,27 boot images or285 shared objects. Avoid another broad baseline scan.

Original logs stay private under the alias in `results.json`; every actual input has a complete SHA. The collector source and persistent offline comparison source are pinned there. No device commands, REA calls, runtime edits or API changes occurred.
