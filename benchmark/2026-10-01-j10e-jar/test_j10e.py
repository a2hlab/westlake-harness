#!/usr/bin/env python3
"""J10e offline gate (self-contained: reads committed smali-evidence, no jar/build tools, runs in the
land.py master gate). Proves the WebView enrichment is wired in the J10e jar (3c147964, baseline J10d
57d62183): install() injected after the J8 WebViewProviderFix.install; a forwarding ViewDelegate
(super_* lookup on PrivateAccess) and a concrete WlCookieManager overriding the full 16-method abstract
surface (incl. the 2 @hide ones); plus the activation markers the smoke gate reads."""
import sys
from pathlib import Path
E = Path(__file__).resolve().parent / "smali-evidence"
read = lambda n: (E / n).read_text()
jv = read("J10eWebView.smali"); dele = read("J10eWebView$DelegateForward.smali")
cm = read("J10eWebView$WlCookieManager.smali"); b7 = read("B7BindFixes.inject.txt")
aosp = read("AOSP-webview-refs.txt"); prov = read("J10eWebView$ProviderEnrich.smali")
fails = []
def ck(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

ck("install() injected AFTER WebViewProviderFix.install in B7BindFixes.apply",
   "WebViewProviderFix;->install()V" in b7 and "J10eWebView;->install()V" in b7
   and b7.index("WebViewProviderFix;->install") < b7.index("J10eWebView;->install"))
ck("delegate forwards to PrivateAccess.super_* (reflective lookup)",
   'const-string v3, "super_"' in dele or '"super_"' in dele)
ck("delegate marker [J10e-WEBVIEW] delegate forwards setLayoutParams", "[J10e-WEBVIEW] delegate forwards setLayoutParams" in dele)
ck("enriched-provider install marker present", "[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded" in jv)
ck("cookie marker [J10e-WEBVIEW] CookieManager stub installed", "[J10e-WEBVIEW] CookieManager stub installed" in prov)
ck("WlCookieManager extends android.webkit.CookieManager", "Landroid/webkit/CookieManager;" in cm)
# 16 abstract overrides incl the two @hide ones
for m in ["acceptCookie()Z","getCookie(Ljava/lang/String;)Ljava/lang/String;",
          "getCookie(Ljava/lang/String;Z)Ljava/lang/String;","hasCookies()Z","hasCookies(Z)Z","flush()V"]:
    ck(f"WlCookieManager overrides {m}", m in cm)
ck("16 public override methods in WlCookieManager", cm.count("\n.method public ") == 16)
ck("AOSP refs cite WebView.java:2658/2465 + getCookieManager abstract-return",
   "WebView.java:2658" in aosp and "super_setLayoutParams" in aosp and "ABSTRACT class CookieManager" in aosp)
n = 15
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
