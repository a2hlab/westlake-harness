# Wikipedia welcome-page instability: TLS-shim + tagsoup (cc-wiki #80, 5ea Wikipedia-line board)

Evidence: 32df×r17p run `runs/32df-5ea-main-20260930T065214/5ea34a45…/wikipedia/hilog.txt` (welcome page 全世界的知识 rendered at t5, self-read; process System.exit(1) before t20).

## Causal chain (self-read stacks)

1. **InitialOnboardingActivity (welcome page "全世界的知识") is the FOREGROUND window** (SCB persistentId 312) and renders fine — it is static, needs NO network. This is why t5 shows the welcome page.
2. **In the background, MainActivity's feed composes** (`org.wikipedia.feed.HomeFragment → HomeScreen → CommunityContentTab`). The feed content fetch is an okhttp async call on a background dispatcher thread (tid 19404) through `org.wikipedia.dataclient.ServiceFactory$LanguageVariantHeaderInterceptor`.
3. **TLS-shim has no real networking**: `com.android.internal.os.TlsShimProvider$ShimSocketFactory.createSocket` (TlsShimProvider.java:116) → `.fail` (:104) throws `UnsupportedOperationException: TLS shim: no real networking (construct-only SSLContext on OH)` → okhttp `ConnectPlan.connectTlsEtc` → `IOException: canceled`.
4. **Feed falls to its error card**: `ForYouCardKt.ErrorState → WikiErrorView → org.wikipedia.language.LanguageUtil.fromHtml → android.text.Html.fromHtml (Html.java:235)`.
5. **tagsoup stub**: `Html.fromHtml` → `org.ccil.cowan.tagsoup.Parser.setProperty(String,Object)` **NoSuchMethodError** (Parser is a constructor-only stub in `/system/android/framework/adapter-mainline-stubs.jar`, boot-AOT).
6. Uncaught on main Thread-1 → `System.exit(1)` → whole process dies → the foreground welcome page is destroyed (SCB `requestSceneContainerDestructionWithTransition` 72348).

## Conclusion: the welcome page does NOT crash itself — the background feed's error card crashes the process.

Therefore the welcome page can be STABILIZED without networking, by fixing the error-card's Html.fromHtml/tagsoup path.

## Mitigations (ranked by cost, for cc-t3)

1. **JAR-level `Html.fromHtml` fallback** (cheapest for a STABLE welcome page): wrap/override so a `NoSuchMethodError` from the tagsoup stub is caught and falls back to a plain-text strip (return the unparsed/spanned text). Then the feed error card renders ("network error" UI) without crashing → process survives → welcome page stays on screen. This is oc-t4's earlier tagsoup line + cc-t3 JAR domain. (The abandoned v7 MainLooperGuard tried to tolerate this at the Looper level and failed on nested Looper.loop; a fromHtml-site fallback avoids that.)
2. **Real tagsoup in boot image** (adapter-mainline-stubs.jar → real `org.ccil.cowan.tagsoup.Parser.setProperty`): boot AOT rebuild. Heavier; same stability outcome as (1).
3. **Real TLS networking** (replace `TlsShimProvider$ShimSocketFactory` with a real socket factory, e.g. WestlakeSSLSocketFactory/OhTrustBridge from the earlier TLS line): the feed loads real content → NO error card → Html.fromHtml/tagsoup never reached, AND the feed itself lights. Fullest win (welcome page + feed both functional), but the hardest (real TLS wiring into OH networking).

## Recommendation
- For a **stable Wikipedia welcome page on screen** (B11 goal), option 1 (fromHtml fallback, cc-t3 JAR) is the cheapest and sufficient — welcome page needs no network.
- For a **functional Wikipedia** (welcome → feed with content), option 3 (real TLS) is required — separate, larger effort.
- Both confirm the outer ring's hypothesis: networking working → feed loads → bypasses Html.fromHtml (opt 3); tagsoup bypass → error card renders without crash (opt 1/2).

## Board dependency
The welcome page only renders with the 32df runtime (which solves the 5ea EGL double-create abort). On the rolled-back 9e14bf20 runtime, wikipedia hwui-aborts at render bring-up and never reaches the welcome page. So welcome-page work requires 32df on 5ea (re-applied as the Wikipedia-line board).
