# T106B — later HAP evidence, initial failure preserved

Actual input is `cc/hap-corrected/hap_corrected.json` (the initially supplied `cc/hap-corrected.json` does not exist). Independent checker rc0;37 input files pinned. Six actual commands: two empty-held rc1, four fresh_ps/HAP reads rc0. Raw receipt interval20:37:06.718326→20:37:07.346736 is0.628410s.

Both mapped host HAP backing files are54,215 bytes and SHA `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`.61b host4958 birth10879, dev/inode66352:545751;5cd host19801 birth2115862, dev/inode66352:211807. Fresh unique host PID, exact serial, in-read birth bracket, maps path and matching stat/SHA/stat are independently checked. Both file stats remain unchanged. The fresh boot is checked before the read; no unrecorded boot-after assertion is added.

This subsequent evidence resolves the two-board HAP comparison only. Initial unknown and both malformed hap_supp attempts remain unchanged. Existing18 mapped-core comparison remains separate;9 BCP JARs/order still unknown, and no timing-cause or swap recommendation follows.

Reproduce `check_hap.py --input <cc/hap-corrected> --output <new result>`. Original invocation/output/rc are private and indexed. Zero device or Git calls; no earlier result overwritten.
