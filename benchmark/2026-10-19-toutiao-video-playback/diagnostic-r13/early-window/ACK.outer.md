# ACK r13-early-evidence-ready — archive closure

Outer executed the exact three prepared argv arrays; all three returned rc0 with empty stderr. Remote SHA256 and size readback match the previously verified local archive: `4c3bbc74f887b05998b7a3a40533f82f1e4bca5424421007ba6932f124e30f37`, 2,281,380 bytes, 4,825 locally verified members.

The lane rc255 denial, original receipt, original ACK/README, manifest, SHA list and 36-file landing remain byte-for-byte unchanged. This success sidecar supersedes only their pending remote-upload status. No archive was rebuilt; no device calls, MAIN edits or push occurred.

`archive/outer-receipt.json` is the exact outer receipt. `archive/outer-evidence-index.json` pins all 13 original command/log/receipt files using a portable private-location alias. Remote raw paths are not published. Use `landing-final-paths.txt` for the combined original delivery plus six closure files; `manifest.final.json` and `SHA256SUMS.final` bind this final collection.

Evidence conclusion remains RESTORED_NO_ATTACH_NO_SAMPLES, not playback PASS. Original facts retain alive_unknown=2.
