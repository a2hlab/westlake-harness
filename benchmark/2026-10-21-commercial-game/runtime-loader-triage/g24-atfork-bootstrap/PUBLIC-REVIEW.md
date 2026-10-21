# Public derivation and independent review

The original bootstrap v1 was independently checked against 25 raw and 14 source pins; three exact objdump commands reproduced the original stdout. One future negative test incorrectly assumed every unversioned provider must fail. The v2 correction now separates the candidate LIBC-version admission requirement from platform matching behavior; original v1 and review evidence were preserved. The independent v2 delta review confirmed the remaining payloads and eight other cases unchanged.

This public copy omits one original stderr log under repository policy. source-manifest.json and source-landing-paths.txt retain the original v2 declaration; the public manifest records the exclusion. remote-archive-v1.json identifies the verified archive containing the original v1 and atfork evidence; v2 is the version-correction.json delta recorded here.

The host namespace chain is static evidence. The proposed compatibility leaf is not implemented, tested or selected over the separate native-cluster comparison.
