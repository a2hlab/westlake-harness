# Retained negative run

The first AArch64 structural run correctly stopped before acceptance because the
hardcoded-owner mutant detector only recognized objdump's hexadecimal immediate
`#0x28`, while this frozen llvm-objdump renders the same instruction as decimal
`#40`.

The verifier was corrected to reject both renderings. No registry/product source
or acceptance invariant was weakened. The next and subsequent full runs killed
the hardcoded-owner mutant and passed all target gates.
