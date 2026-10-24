# T122 — ordinary startup suffix review

**New explicit response-parsing exception; no implementable public API candidate.** Identity checks pass for both complete files. Only newly added suffixes were semantically reviewed; no device, deployment, source implementation or stopped-object access occurred.

Evidence root: `$HOME/.local/share/westlake/t122-hdc-outer-check-20261024/collection-01/`. Line numbers below refer to **unwrapped complete payload files**, not the old collector's five-line header. T95 comparator: `$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout` (child6291,4MiB,SHA `2ee3a988…`).

| Evidence | 7011-payload.stdout | 9860-payload.stdout | T95 comparison / limit |
|---|---|---|---|
| Complete file / new suffix | 368251 bytes;237179 new; lines1589–4451 | 314796 bytes;183724 new; lines1511–3710 | First suffix line crosses the old byte boundary and is reconstructed; both files end in newline |
| Explicit JSON conversion exception | **2459**, stack2460–2464 | **2633**, interleaved stack2635–2639 | No `org.json.JSONException:` in T95's captured prefix |
| WMC createSession / RS node-create flush | 2698/2701;4284/4286 | 2703/2706 | T95 createSession4259/7152; first node-create flush4287 |
| Selected `EglManager::swapBuffers ENTRY` marker | Not found in suffix | Not found in suffix | T95 first6945; missing marker is not proof of no rendering or its cause |

Both exceptions state `Value <html><head><title>302 of type java.lang.String cannot be converted to JSONObject`, with stack through `com.ss.android.article.news.launch.codeopt.LJSONObject` and `com.jdwx.sdk.util.b.run`. This is an actual exception plus stack, not a keyword hit in response prose. **The title text does not establish an HTTP302 status.** There is no bound request URL, headers/content type, redirect handling, main-feed consumer or public API contract violation. A JSON parser rejecting HTML is not itself a demonstrated parser defect. No implementation search or patch is justified yet. Ordinary WMC/RS progress appears later in file order, without proving this exception harmless or fatal.

Other concrete failures are shared with success: `libnetworkpredictor`1695/2029 vs T95 3135; `libwasm`1880 vs2080; `libttopenssl`1930/2156 vs3218; avmdl-family missing libraries; lynx bridge dependency2002 vs2149; `libquick`3250/3170 vs6285; ICU symbol2697/2702 vs4258; getprop2752/2310 vs13009; resource-close warnings also occur in T95. Complete line lists are in `results.json`. Shared presence limits discrimination; it does not rule out timing/state-specific effects.

Network terms were retained rather than excluded: suffix connect records contain result−1/errno115 (17 and15 records), and result0/errno0 (4 and2). T95's captured connect records instead show result−1/errno101. These are numeric operation results, not independently established fatal network-service failures. Different network conditions and unmatched requests prevent a controlled comparison; no addresses, tokens or response bodies are published.

Identity: full SHA `712a2545…` / `6b7da32c…`, exact old131072-byte prefixes, old/new dev/inode/size/mtime/ctime equality, stable collection stat, and complete byte counts were independently checked. Historical boot is bound through T109 evidence; collection boot alone is not file birth. Complete files at collection do not guarantee every process-lifetime event was flushed. T95 is another board/run, not successful5cd child7111. No first-frame/Activity-completion or precise cross-clock claim is made; lexical screening is not an exhaustive semantic proof.

The remaining specific gap is the ordinary request/response identity and consumer for the `com.jdwx.sdk` JSON parse. Any further evidence task should bind that operation before choosing an API target; this review performs no new collection.

Reproduce: `python3 benchmark/2026-10-24-ordinary-log-suffix/analysis-peer/analyze.py`. The script verifies existing bytes and writes the small adjacent `results.json`; raw logs remain private. A local script syntax error was corrected before the successful run; no evidence files were changed.
