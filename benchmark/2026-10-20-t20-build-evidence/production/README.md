# T20 paired shim production archive

This package preserves the frozen candidate and reproducible incremental build inputs. It is not a deployment admission. Production-03 and production-04 both produced `5cc23582d8cd8f28b24f89dc9bcf439de2177c0be33bb4783dd1baad3ab32eca` (70,184 bytes), from pair source `610053541b996e41377aae1270f42eed52610b60e17e5e948c2f297a78aa2155`. The baseline relink is exact `85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a`.

All 104 input pins were checked against actual files and included under portable archive roots, including compiler/linker/readobj bytes, headers, original ASM object, CRT/builtins and libc/libdl inputs. Both successful builds have all 16 original argv/stdout/stderr/rc groups, 32 groups total, with rc0; all eight artifacts per build match the receipts. No build was repeated by this evidence lane.

The author's raw index expanded from the dispatch-time 470 to 635 entries while the source closure was finalized. All 635 entries were checked and archived, plus 55 extra local raw files explicitly indexed. Failures and intermediate candidates remain distinct. The initial count refusal occurred before a tar was created and is retained privately. The source snapshot is checked against MAIN commit `4b17ff7861fa1c16b5874594db11e97d68ef73f9`.

Peer source is read from immutable commit `6d37c756cb698708d86f7e9d7ecf3b9ec5a779ea`. Its replay_pair.py is byte-identical to the earlier 1315b21a test_pair.py; README/landing rename changes do not change review facts. Its ten-case results and exact raw receipts are preserved, including earlier failed counterexamples. The archived peer status is SCOPED_STATIC_AND_HOST_ACCEPT, with loader/provider seams and runtime limitations intact.

The archive also preserves source, license, derivation, recipe, source comparison and ELF evidence. New baseline/object reconstruction logs are not the missing historical original85 execution logs. Reusing original ASM/CRT/library inputs is not a whole-platform rebuild. T18 human audio evidence is historical context only; no T20 video or runtime success is inferred.

The final archive is `.private/archive-03/production.tar.gz`. Every one of its 983 members was read back and verified. Prior package-02 is locally retained but superseded by the latest peer rename and was not uploaded. The original checkpoint remains unchanged.

The lane's first SSH command returned rc255; no subsequent transfer ran. `upload-attempt/` preserves its sanitized public sidecar and exact private SHA index. `packet/archive-receipt.json` stays LOCAL_VERIFIED_REMOTE_PENDING until outer completes the three exact argv in `.private/archive-03/remote-commands.private.json`. No device operations or pushes occurred.
