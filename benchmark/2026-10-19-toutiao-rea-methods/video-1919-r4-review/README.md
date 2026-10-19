# r4 independent artifact review

The r3 crash report frame offset was not an ELF virtual address. Reconciliation of PC, mappings and PT_LOAD identified the store at ELF 0xde714; its argument names eglPresentationTimeANDROID. A provider function preempted a player OBJECT cache address. The original failed run remains unchanged.

The independently derived output matches the executed candidate: 4,662,040 bytes, 105 relocation entries, 627 differing bytes, zero differences outside those entries’ r_info/r_addend fields. The symbol table, hashes, code and permissions remain byte-identical. Only one fault was observed; the 105 entries form a potential collision family.

- [Independent relocation rows](independent-relocations.json)
- [Artifact result](results.json)
- [Persistent raw execution and artifact hashes](persistent-artifacts.json)
- [Committed derivation recipe](../../2026-10-19-toutiao-video-playback/candidate-r4/derive_ttmplayer_selfrel.py)
- [Candidate and reproduction notes](../../2026-10-19-toutiao-video-playback/candidate-r4/README.md)

Original command, stdout, stderr, rc=0, executed recipe, input and output are retained in the persistent local receipt and mirrored to the operator-configured hw248 artifact root; eight remote file hashes were verified. The public placeholder is not a pre-existing environment variable mapping. Exact physical location is retained in the private receipt.

This review accepts only the static artifact. It does not prove player loading, dynamic video, sound, API freezing or full application support. The four-file executor and real-device result have separate admission and evidence.
