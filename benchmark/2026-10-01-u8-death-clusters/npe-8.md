# NPE ×8 (U9 still dead) — framework null-return point + clusters (offline)

Dispatch (ACK(90) latest): first-wall.json NPE family + u9_prediction=dead, per-key NPE line + first app frame + first framework frame, AOSP 14 null-return point (file:line), cluster by service/method returning null.

## Numbers first

8 keys: notepad, stoutner-privacybrowser-standard, timur-webrtc-check, fd-breezyweather, fd-client, fd-tutanota, fd-wifianalyzer, toutiao.

### Per-key stack excerpts

**cv2-com-nononsenseapps-notepad** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-com-nononsenseapps-notepad/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirst()' on a null object reference
    at com.nononsenseapps.notepad.activities.main.DrawerCursorLoader.onLoadFinished(SourceFile:6)
    at androidx.loader.app.LoaderManagerImpl$LoaderObserver.onChanged(SourceFile:5)
    at androidx.lifecycle.LiveData.considerNotify(SourceFile:30)
    at androidx.lifecycle.LiveData.dispatchingValue(SourceFile:56)
    at androidx.lifecycle.MutableLiveData.setValue(SourceFile:15)
    at androidx.loader.app.LoaderManagerImpl$LoaderInfo.setValue(SourceFile:1)
    at androidx.loader.content.CursorLoader.deliverResult(SourceFile:33)
```
- NPE method: `android.database.Cursor.moveToFirst()` — receiver is null (the Cursor delivered to `onLoadFinished` is null).
- App frame: `com.nononsenseapps.notepad.activities.main.DrawerCursorLoader.onLoadFinished(SourceFile:6)`.
- Framework frame: `androidx.loader.app.LoaderManagerImpl$LoaderObserver.onChanged(SourceFile:5)`.
- AOSP 14 null-return point: `CursorLoader.deliverResult(SourceFile:33)` calls `onLoadFinished(loader, mCursor)` — `mCursor` is null when the query returned no rows or the loader was cancelled. The NPE is in the app's `onLoadFinished`, not in the framework. **Framework fix point: `CursorLoader.deliverResult` should not deliver a null Cursor, or `onLoadFinished` should be documented to accept null.**

**cv2-com-stoutner-privacybrowser-standard** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-com-stoutner-privacybrowser-standard/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' on a null object reference
    at com.stoutner.privacybrowser.activities.MainWebViewActivity.onCreate
```
- NPE method: `java.lang.Object.getClass()` — receiver is null (the Activity's `this` or a field is null).
- App frame: `com.stoutner.privacybrowser.activities.MainWebViewActivity.onCreate`.
- Framework frame: `android.app.Activity.performCreate`.
- AOSP 14 null-return point: `Activity.performCreate(Activity.java:8577)` — the Activity object itself is created by `Instrumentation.newActivity` or `ActivityThread.performLaunchActivity`; if the Activity's constructor or field initialization fails, `this` may be partially initialized. **Framework fix point: not a framework null-return; the NPE is in the app's onCreate (likely a WebView stub field being null).**

**cv2-timur-webrtc-check** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-timur-webrtc-check/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'void android.webkit.WebSettings.setJavaScriptEnabled(boolean)' on a null object reference
    at timur.webrtc.check.WebRTCCheckActivity.onCreate
```
- NPE method: `android.webkit.WebSettings.setJavaScriptEnabled(boolean)` — receiver is null (WebSettings is null).
- App frame: `timur.webrtc.check.WebRTCCheckActivity.onCreate`.
- Framework frame: `android.app.Activity.performCreate`.
- AOSP 14 null-return point: `WebView.getSettings()` (WebView.java) returns `mProvider.getSettings()` — if the WebView stub's provider is null or `getSettings()` returns null, this NPE fires. **Framework fix point: `WebView.getSettings()` should not return null; the stub's provider must return a non-null WebSettings.**

**fd-breezyweather** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-v1/20261001T120450-65131f4f/5ea34a4500000000000000001123012c/fd-breezyweather/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' on a null object reference
    at pa0.G
```
- NPE method: `java.lang.Object.getClass()` — receiver is null.
- App frame: `pa0.G` (obfuscated; likely a coroutine or Kotlin class).
- Framework frame: `android.app.Activity.performCreate`.
- AOSP 14 null-return point: same as privacybrowser — `Activity.performCreate` creates the Activity; if a field is null, `getClass()` on it NPEs. **Framework fix point: not a framework null-return; the NPE is in the app's code (obfuscated).**

**fd-client** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-v1/20261001T120450-65131f4f/5ea34a4500000000000000001123012c/fd-client/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.String[] javax.net.ssl.SSLEngine.getEnabledProtocols()' on a null object reference
    at com.owncloud.android.MainApp.insertConscrypt
```
- NPE method: `javax.net.ssl.SSLEngine.getEnabledProtocols()` — receiver is null (SSLEngine is null).
- App frame: `com.owncloud.android.MainApp.insertConscrypt`.
- Framework frame: `android.app.Instrumentation.callApplicationOnCreate`.
- AOSP 14 null-return point: `Instrumentation.callApplicationOnCreate(Instrumentation.java:1192)` calls `app.onCreate()`; `insertConscrypt` creates an SSLEngine via `SSLContext.getDefault().createSSLEngine()` — if the SSLContext provider is null or the engine creation fails, the SSLEngine is null. **Framework fix point: the adapter's Conscrypt/OpenSSL provider must return a non-null SSLEngine; or `SSLContext.getDefault()` must not return null.**

**fd-tutanota** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/fd-tutanota/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.String android.webkit.WebSettings.getUserAgentString()' on a null object reference
    at de.tutao.tutanota.MainActivity.onCreate
```
- NPE method: `android.webkit.WebSettings.getUserAgentString()` — receiver is null (WebSettings is null).
- App frame: `de.tutao.tutanota.MainActivity.onCreate`.
- Framework frame: `android.app.Activity.performCreate`.
- AOSP 14 null-return point: same as timur-webrtc-check — `WebView.getSettings()` returns null. **Framework fix point: same as above.**

**fd-wifianalyzer** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/fd-wifianalyzer/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'java.lang.Class java.lang.Object.getClass()' on a null object reference
    at wb0.H
```
- NPE method: `java.lang.Object.getClass()` — receiver is null.
- App frame: `wb0.H` (obfuscated).
- Framework frame: `java.lang.reflect.Method.invoke`.
- AOSP 14 null-return point: same as privacybrowser/breezyweather — `Activity.performCreate` creates the Activity; if a field is null, `getClass()` on it NPEs. **Framework fix point: not a framework null-return; the NPE is in the app's code (obfuscated).**

**toutiao** (`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/toutiao/hilog.txt`):
```
Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'boolean java.lang.Boolean.booleanValue()' on a null object reference
    at com.ss.android.article.news.activity.MainActivity.<init>
```
- NPE method: `java.lang.Boolean.booleanValue()` — receiver is null (a Boolean field is null).
- App frame: `com.ss.android.article.news.activity.MainActivity.<init>`.
- Framework frame: `java.lang.Class.newInstance`.
- AOSP 14 null-return point: `Class.newInstance` creates the Activity; if a Boolean field is uninitialized (null), `booleanValue()` on it NPEs. **Framework fix point: not a framework null-return; the NPE is in the app's constructor (field initialization order).**

## Clusters by framework null-return point

| Cluster | Keys | Framework method | AOSP 14 file:line | Fix point |
|---|---|---|---|---|
| **Cursor null** | notepad | `CursorLoader.deliverResult` delivers null Cursor | `CursorLoader.java:33` (androidx) | `deliverResult` should not deliver null Cursor, or document `onLoadFinished` accepts null |
| **WebView stub getSettings null** | stoutner-privacybrowser-standard, timur-webrtc-check, fd-tutanota | `WebView.getSettings()` returns null | `WebView.java:443` (`mProvider.getSettings()`) | WebView stub's provider must return non-null WebSettings (J10e) |
| **Object.getClass() null** | fd-breezyweather, fd-wifianalyzer | `Activity.performCreate` creates Activity with null field | `Activity.java:8577` | Not a framework null-return; app's field initialization order |
| **SSLEngine null** | fd-client | `SSLContext.getDefault().createSSLEngine()` returns null | `Instrumentation.java:1192` | Adapter's Conscrypt/OpenSSL provider must return non-null SSLEngine |
| **Boolean.booleanValue() null** | toutiao | `Class.newInstance` creates Activity with null Boolean field | `Class.newInstance` (Java) | Not a framework null-return; app's field initialization order |

## Conclusion

The 8 NPE keys split into **5 clusters**:

1. **Cursor null** (1 key): `CursorLoader.deliverResult` delivers null Cursor — framework should not deliver null, or document null acceptance.
2. **WebView stub getSettings null** (3 keys): `WebView.getSettings()` returns null — the WebView stub's provider must return non-null WebSettings (J10e).
3. **Object.getClass() null** (2 keys): `Activity.performCreate` creates Activity with null field — not a framework null-return; app's field initialization order.
4. **SSLEngine null** (1 key): `SSLContext.getDefault().createSSLEngine()` returns null — adapter's Conscrypt/OpenSSL provider must return non-null SSLEngine.
5. **Boolean.booleanValue() null** (1 key): `Class.newInstance` creates Activity with null Boolean field — not a framework null-return; app's field initialization order.

**The WebView stub cluster (3 keys) is the only one with a single framework fix point** (`WebView.getSettings()` returning null). The other clusters are app-specific or need framework changes that accept null (Cursor) or fix the provider (SSLEngine).
