# T23 outer upload success

The prior receipt records the earlier local-verification stage and remains unchanged. The outer operator subsequently executed the three upload commands: all returned rc 0. Remote SHA-256 and size match the locally verified archive: `bc98710eb4927a9189f34bc9c2fd22ad147467a18265d24224d43cebd94921a3`, 5,537,895 bytes.

The first actual command adds `test ! -e <remote archive> &&` before the planned directory creation. It is not byte-identical to the planned argv. The second and third raw argv exactly match the plan. This precheck is evidence of the executed guard, not a claim of atomic no-clobber upload.

`sanitized-envelopes.json` preserves the three actual argv and streams with only home/artifact-root aliases substituted. `raw-index.json` pins the private original bytes and records those substitutions, plus unchanged historical archive files. These recorded aliases are not runnable commands. `results.json` states the narrow remote verification result. The original pending receipt, candidate source, production results and pins were not edited; this receipt adds no deployment or playback claim.
