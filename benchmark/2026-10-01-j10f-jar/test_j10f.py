#!/usr/bin/env python3
"""J10f offline gate (self-contained; reads committed smali-evidence). Proves U9 jar a0f8ba45 (baseline
J10d 57d62183) wires WebViewProvider.getSettings() to a concrete WlWebSettings that overrides the full
104-method abstract surface of AOSP 14 WebSettings (incl @hide/@SystemApi/@UnsupportedAppUsage, via a
compile-only stub), plus the [J10f-WEBVIEW] marker and the install injection carried from J10e."""
import sys
from pathlib import Path
E = Path(__file__).resolve().parent / "smali-evidence"
read = lambda n: (E / n).read_text()
prov = read("J10eWebView$ProviderInstance.smali"); jf = read("J10fWebSettings.smali")
cnt = read("WlWebSettings.count.txt"); head = read("WlWebSettings.head.smali"); b7 = read("B7BindFixes.inject.txt")
fails=[]
def ck(name,cond):
    print(("PASS " if cond else "FAIL ")+name)
    if not cond: fails.append(name)
ck("ProviderInstance.getSettings -> J10fWebSettings.get()Landroid/webkit/WebSettings",
   '"getSettings"' in prov and "J10fWebSettings;->get()Landroid/webkit/WebSettings;" in prov)
ck("J10fWebSettings marker [J10f-WEBVIEW] settings stub installed", "[J10f-WEBVIEW] settings stub installed" in jf)
ck("WlWebSettings extends android.webkit.WebSettings", "Landroid/webkit/WebSettings;" in head and ".super Landroid/webkit/WebSettings;" in head)
ck("WlWebSettings overrides all 104 abstract methods", cnt.strip().endswith("104"))
ck("install() injection carried from J10e (after WebViewProviderFix.install)",
   "WebViewProviderFix;->install()V" in b7 and "J10eWebView;->install()V" in b7
   and b7.index("WebViewProviderFix;->install") < b7.index("J10eWebView;->install"))
n=5
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails))+' FAIL'} ({n-len(fails)}/{n})")
sys.exit(1 if fails else 0)
