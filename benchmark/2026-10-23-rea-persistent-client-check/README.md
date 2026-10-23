# Persistent REA client check

The earlier failed client and the T55 nine-member list must not be used to conclude that this newly loaded session cannot execute REA or that a ten-occurrence summary reveals missing code.

This persistent conversation actually completed exactly three REA calls: `open_binary`, `inspect_artifact` with `detail: summary`, and `close_binary`. No client rejection occurred. The original tool-return objects are preserved in `01-open.response.json`, `02-inspect-summary.response.json`, and `03-close.response.json`; `results.json` pins their hashes. The close response is `{"result":null}`. This was a new invocation in this conversation, not a copy of the fresh-client recovery receipt. Configuration recovery was separately published at `09b3224cf6`.

Both T55 and this invocation identify HAP SHA `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`. T55 lists **9 named members**, with **8 distinct member hashes**: its two icon paths share bytes. REA reports **10 file occurrences, 9 nodes, 9 edges, 0 integrity contradictions**. Its summary Evidence is `ev_a10151d6e3dc9775d185fe96cf8506f09f1710a2550ca90f67b6d4f31d43d635`.

The summary contains no occurrence paths or graph records. **The identity of the tenth occurrence and the exact member mapping are unknown.** Root inclusion and content deduplication are plausible count explanations, not verified mappings. Do not equate graph occurrences with ZIP member count or infer missing code from this difference. No further inspection was performed.

This proves successful execution of these three tools in this session. It does not prove future-session availability, other-tool availability, ArkABC semantics, current installed identity, runtime behavior, or a white-screen fix. No board access, runtime/configuration change, T71/T74 continuation, commit or push occurred. Raw receipts retain original local paths and have not been prepared for public publication.
