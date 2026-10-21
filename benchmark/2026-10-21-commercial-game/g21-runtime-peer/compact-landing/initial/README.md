# Initial apply: rejected, service recovery incomplete

Apply returned rc2. Candidate label command 01384 and automatic rollback label command 02293 each reported an unclosed LABEL_RECIPE_INPUT heredoc. Both transport exits were 0 with no remote status marker: remote results remain unknown. The exact failing commands and stdout are in failures/.

All 32 operations were restored, with 30 same-SHA operations and only two logical libnativeloader alias changes. Candidate-after-bind and baseline-after-unmount each matched 319 hashes (hash-stages.json). The mount stack matched the before-image. No appspawn-x start command was issued and the final process table contained none. This historical recovery_required result is not rewritten by later recovery.

The immutable failed journal SHA is e4ead80b9dfe744df841309a5e928cf2a03981380412f7955657012517e3ca95. All original receipts, including the omitted large stderr and journal, are indexed in ../original-sha-index.json.gz under the persistent private alias documented in ../source-index.json. Initial label before-audits: candidate 29 mismatches, baseline zero; neither has an after-audit. See ../label-summary.json. Shared label scope alone is not direct in-memory manifest proof.
