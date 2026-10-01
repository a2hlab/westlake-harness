#!/usr/bin/env python3
"""Generate a compile-only android.webkit.WebSettings stub + adapter.activity.J10fWebSettings
(with inner WlWebSettings overriding every abstract method) by PARSING AOSP 14 WebSettings.java.
Hand-writing 105 abstract methods (incl @hide/@SystemApi/@UnsupportedAppUsage) is error-prone; the
runtime abstract surface must be matched exactly or `new WlWebSettings()` throws InstantiationException."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/lab"))
import lab_paths  # noqa: E402
SRC = (lab_paths.workspaces() / "westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/webkit/WebSettings.java")
OUT_STUB = Path(sys.argv[1]); OUT_J10F = Path(sys.argv[2])
raw = SRC.read_text()
# strip block comments and line comments
nocomb = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
nocom = re.sub(r"//[^\n]*", "", nocomb)
# nested enums: 'public enum Name {  A, B, ... }'
enums = []
for m in re.finditer(r"public\s+enum\s+(\w+)\s*\{(.*?)\}", nocom, flags=re.S):
    name = m.group(1); body = m.group(2)
    consts = re.findall(r"\b([A-Z][A-Z0-9_]+)\b", body.split(";")[0])  # constants before any ';'
    # keep order, unique
    seen=[]; 
    for c in consts:
        if c not in seen: seen.append(c)
    enums.append((name, seen))
# abstract methods: 'public abstract <ret> <name>(<params>);' (join multiline, strip annotations inside)
# collapse whitespace
flat = re.sub(r"\s+", " ", nocom)
abstracts = re.findall(r"public abstract ([^;{}]+?)\s*;", flat)
methods = []  # (ret, name, params_str)
for a in abstracts:
    a = a.strip()
    mm = re.match(r"^(.*?)\s+(\w+)\s*\((.*)\)$", a)
    if not mm:
        print("WARN unparsed:", a); continue
    ret, name, params = mm.group(1).strip(), mm.group(2), mm.group(3).strip()
    ann = lambda s: re.sub(r"@\w+(\([^)]*\))?\s*", "", s).strip()
    ret = ann(ret); params = ann(params)
    methods.append((ret, name, params))

def default_ret(ret):
    ret = ret.strip()
    if ret == "void": return None
    if ret == "boolean": return "false"
    if ret in ("int","short","byte"): return "0"
    if ret == "long": return "0L"
    if ret == "float": return "0f"
    if ret == "double": return "0d"
    if ret == "char": return "'\\0'"
    return "null"

# stub
enum_decls = "\n".join(f"    public enum {n} {{ {', '.join(cs) if cs else '_X'} }}" for n,cs in enums)
stub_methods = "\n".join(f"    public abstract {ret} {name}({params});" for ret,name,params in methods)
OUT_STUB.parent.mkdir(parents=True, exist_ok=True)
OUT_STUB.write_text(f"package android.webkit;\npublic abstract class WebSettings {{\n    public WebSettings() {{}}\n{enum_decls}\n{stub_methods}\n}}\n")

# J10fWebSettings with WlWebSettings overrides
ov = []
for ret,name,params in methods:
    d = default_ret(ret)
    body = "" if d is None else f" return {d};"
    ov.append(f"        @Override public {ret} {name}({params}) {{{body} }}")
overrides = "\n".join(ov)
j10f = f'''/* J10f (#webview-settings): single-purpose file (freeze unit) -- concrete WebSettings so
 * WebViewProvider.getSettings() is non-null (route-A WebView apps call getSettings().setJavaScriptEnabled
 * before use). All {len(methods)} abstract methods overridden (generated from AOSP 14 r1 WebSettings.java;
 * getters -> type-zero defaults, setters -> no-op). Built via a compile-only android.webkit.WebSettings
 * stub (the real abstract surface includes @hide/@SystemApi/@UnsupportedAppUsage methods absent from
 * public android.jar). Wired from J10eWebView.ProviderInstance.getSettings(). */
package adapter.activity;

import android.webkit.WebSettings;

public final class J10fWebSettings {{
    private J10fWebSettings() {{}}
    private static volatile boolean sLogged = false;
    private static volatile WebSettings sSettings;

    /** Called from J10eWebView.ProviderInstance.getSettings(). Returns a cached concrete WebSettings. */
    public static WebSettings get() {{
        if (sSettings == null) sSettings = new WlWebSettings();
        if (!sLogged) {{ sLogged = true; System.err.println("[J10f-WEBVIEW] settings stub installed"); }}
        return sSettings;
    }}

    static final class WlWebSettings extends WebSettings {{
{overrides}
    }}
}}
'''
OUT_J10F.write_text(j10f)
print(f"enums: {[n for n,_ in enums]}")
print(f"abstract methods parsed: {len(methods)}")
print(f"stub -> {OUT_STUB}")
print(f"j10f -> {OUT_J10F}")
