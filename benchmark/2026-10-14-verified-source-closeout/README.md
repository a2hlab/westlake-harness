# Verified implementation source closeout

Earlier delivery linked reports or deployment scripts for some validated implementations while leaving their producing code and input preparation in worker trees. This closeout records actual implementations, executable recipes, SHA-pinned inputs and newly captured execution logs separately from historical deployment claims.

| Delivered component | Source and build entry | New verification |
| --- | --- | --- |
| J10d manifest theme | [Java, caller patch and builder](../../sources/api-implementations/JAVA-033-theme/README.md) | Full historical JAR57d62183 exact; repeated from the input archive. |
| Signed Boat C9 JAR | [Original producer and prepared inputs](../../sources/api-implementations/boat-c9-jar/README.md) | Full signed JAR6333bcab exact, original producer builds twice; repeated from the input archive. |

[Independent scope audit](root/extra-source-audit.json) and [persistence receipt](root/persistence.json). Raw failures are retained alongside successful executions in the pinned durable archive. The local durable root is `$WORKSPACES/_verified-source-closeout-20261014`; no useful result relies solely on `/tmp`. Source and small execution receipts are committed here; binary inputs and raw private execution archives are stored on hw248 with SHA locks.

The concurrent Boat native, shared native and J1/J7b closeout packets are reviewed separately before integration. This is not a claim that every unknown API or every vendor library has been implemented or rebuilt.
