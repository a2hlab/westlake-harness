# split-equivalence — split U10-base jar vs J10g 238ffc14 (method-body diff, class names normalised)

OLD (J10g) sha256 238ffc14… = `238ffc148620ab5a1311c0cdb4fb7eddc50a9ae69a8465744c1824dcc8b01426`
NEW (split U10-base) sha256 = `11974b7b2f1af41b7dfe116ceac23f0db3c3b2a677acd4418aecc72457dcf123`

Class tokens `J10eWebView$DelegateForward`↔`J10eViewDelegate` and `J10eWebView$WlCookieManager`↔`J10eCookieManager` are normalised to `<DELEGATE>`/`<COOKIE>`. A method is **IDENTICAL** if its body matches after that normalisation.

| old class | method | verdict |

**150 methods IDENTICAL (mod class names); 2 differ (detailed below).**

|---|---|---|
| J10eWebView$DelegateForward | public invoke(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object; | DIFFERS → old:['invoke-static {}, Ladapter/activity/J10eWebView;->access$300()Z', 'invoke-static {v2}, Ladapter/activity/J10eWebView;->access$302(Z)Z'] new:['sget-boolean p3, <DELEGATE>->sLoggedDelegate:Z', 'sput-boolean v2, <DELEGATE>->sLoggedDelegate:Z'] |
| J10eViewDelegate | static constructor <clinit>()V | NEW-ONLY |
| J10eWebView$WlCookieManager | constructor <init>()V | OLD-ONLY (removed) |
| J10eCookieManager | public constructor <init>()V | NEW-ONLY |
| J10eWebView | static constructor <clinit>()V | DIFFERS → old:['sput-boolean v0, Ladapter/activity/J10eWebView;->sLoggedDelegate:Z'] new:[] |
| J10eWebView | static synthetic access$300()Z | OLD-ONLY (removed) |
| J10eWebView | static synthetic access$302(Z)Z | OLD-ONLY (removed) |

## Conclusion — behaviour-identical

**150 method bodies are instruction-identical** after normalising (a) the two renamed class tokens
`<DELEGATE>`/`<COOKIE>` and (b) debug directives (`.line`/`.local`/`.registers`) and label offsets
(positional noise from recompiling at new source line numbers). The complete set of remaining differences,
all a direct consequence of relocating the single `private static volatile boolean sLoggedDelegate` flag
out of `J10eWebView` into its natural owner `J10eViewDelegate`, with **no behaviour change**:

1. `J10eViewDelegate.invoke` (was `J10eWebView$DelegateForward.invoke`): reads/writes the flag via
   `sget-boolean/sput-boolean J10eViewDelegate->sLoggedDelegate` instead of `J10eWebView`'s synthetic
   accessors `access$300()/access$302()`. Same flag, same read-once-then-set semantics (gates the
   one-time `[J10e-WEBVIEW] delegate forwards setLayoutParams` log).
2. `J10eWebView.<clinit>` no longer initialises `sLoggedDelegate` (the flag's `<clinit>` init moved to
   `J10eViewDelegate`).
3. `J10eWebView.access$300()` / `access$302()` removed — they existed only to let the former inner class
   read/write the outer private flag; unneeded once the flag lives in `J10eViewDelegate`.
4. `J10eCookieManager.<init>` is `public` (top-level) where `J10eWebView$WlCookieManager.<init>` was
   package-private (inner) — a visibility widening from the inner→top-level move; body (super() call) identical.

Everything else — all 16 `J10eCookieManager` override bodies, the `ProviderEnrich`/`ProviderInstance`/
`ZeroH` invoke bodies (incl. the `new J10eViewDelegate` / `new J10eCookieManager` sites, which differ only
in the normalised class token), `J10eWebView.install`/`zero`, and the untouched `J10fWebSettings*` /
`J10gWebExtras*` — is byte-identical. The split is behaviour-preserving; `oh-adapter-runtime-u10base.jar`
(`11974b7b…`) is a clean U10 base.

## Class-list diff (dexdump, outer-loop requested)

`dexdump` class descriptors of both `classes.dex`, sorted unique:

- **old (J10g 238ffc14): 185 classes · new (U10 base 11974b7b): 185 classes · 183 identical**
- **Added in U10 base (2):** `adapter/activity/J10eCookieManager`, `adapter/activity/J10eViewDelegate`
- **Removed from 238ffc14 (2):** `adapter/activity/J10eWebView$DelegateForward`, `adapter/activity/J10eWebView$WlCookieManager`

The two removed inner classes are exactly the two added top-level classes (the ViewDelegate and
CookieManager fixes, relocated out of `J10eWebView`). **No other class is added, removed, or renamed** —
the remaining 183 classes (incl. all `J10eWebView$*` provider-seed inner classes, `J10fWebSettings*`,
`J10gWebExtras*`, and the entire untouched baseline) are set-identical. Confirms the split is a pure
two-class relocation, nothing else moved.
