# M2 route-a loader placement: the namespace permission rule, where each component sits, and the minimal fix (target the `nweb_ns` name) — no frozen file changed

#90, offline (outer 11:21). A0 on-board is paused; this decides where route a's NWeb loader runs, statically. No board
window. For outer approval before window 10.

## ① The permission rule (`evidence/musl-permission-rule.txt`; OH 6.1.0.31 `$OH610/third_party/musl/ldso/linux/dynlink.c`)

`dlns_create2` (line 4907), `dlopen_ns` (4864), `dlns_create` (4953 → `dlns_create2(…, CREATE_INHERIT_DEFAULT)` 4956),
and the `dlns_*`/`dlopen` family (4823, 4881, 4968, 5750–5828) all gate on `is_permitted(caller_addr, dlns->name)`
(4208). `is_permitted` → `in_permitted_list(ns->ns_name, target)` (4190), which returns true iff **either**:

- the **caller's own namespace name** is in `dlopen_permitted_list` (4176):
  `default, ndk, system, chipsetsdk, chipsetsdk_sp, vendor, passthrough, passthrough_indirect`; **or**
- the **target namespace name** is `PERMITIED_TARGET` = **`nweb_ns`** (4188) or `nweb_ns_legacy` (4189).

Window 9 failed because the caller ns was `westlake.anl.app.<pid>` (not in the list) and the target was `wl_a0arkweb`
(not `nweb_ns`): `dlns_create2` returned `EPERM` (the `create=1` in the window-9 log is `EPERM`=1), and `dlopen_ns` was
denied. **This is why OH's own loader names its namespace `nweb_ns`** (`arkweb_utils.cpp GetArkwebNameSpace()` →
`"nweb_ns"`): the target-name branch lets it create/open that namespace from any caller.

## ② Where each component sits (`evidence/namespaces-observed.txt`, `open-site-scan-runtime-bridge.txt`)

Namespaces present in an appspawn-x child (window-9 MUSL-LDSO, 5cd U13), judged against the rule:

| namespace | in process | permitted caller? |
|---|---|---|
| `default` | yes (OH system libs; has bare `/system/lib64`, inherits `ndk`) | **yes** |
| `ndk` | yes (`/system/lib64/ndk`) | **yes** |
| `westlake.anl.app.<pid>` | yes — **the entry `System.load`'d via B7BindFixes runs here** | no |
| `westlake.sealed.child` | yes | no |
| runtime-CL classloader ns (B7BindFixes `createClassloaderNamespace`, 4-dir search) | yes | no |

**No westlake-created namespace is a permitted caller.** `open_site_scan` over the deployed runtime 18763dd4 and bridge
84695d62: every fixed-path load site is `ns=caller-default` — the runtime/bridge dlopen into the caller's own default
resolution and **do not create namespaces themselves**, so there is no existing privileged `dlns_create`/`dlopen_ns`
open site to reuse. (The `libart` copies are ART's own, not a route-a loader site.)

So only two mechanisms pass `is_permitted`:
- **(A) target name `nweb_ns`** — permitted from *any* caller, including `westlake.anl.app`;
- **(B)** run the `dlns`/`dlopen_ns` call from a DSO whose own namespace is `default`/`ndk`/`system`/… — which would
  require adding a **new** privileged open site (a frozen-file change), since none exists today.

## ③ Minimal fix (chosen): target the `nweb_ns` name; no frozen file changed

The A0 probe (and route a's loader) keeps loading through the **existing** B7BindFixes `System.load` point and runs in
`westlake.anl.app` — but names its namespace **`nweb_ns`** instead of `wl_a0arkweb`:

1. `dlns_init(&ns, "nweb_ns")`; `dlns_get("nweb_ns", &ns)` first (OH may already have created it) — if absent,
   `dlns_create(&ns, "/data/local/tmp")` (= `dlns_create2(…, CREATE_INHERIT_DEFAULT)`, which inherits `default`, so the
   152-lib closure's 14 `/system/lib64` + `ndk` members resolve). Both pass `is_permitted` via the target-name branch.
2. `dlopen_ns(&ns, "libwl_a0_nweb.so", RTLD_NOW)` — permitted (target `nweb_ns`).
3. `dlsym` `a0_probe_start` as before.

Only the entry's two string constants change (ns name + handling an existing `nweb_ns`); the worker is unchanged. **No
runtime / bridge / BCP / JAR / any frozen file is touched** — the entry is still a window-only bind-mount at the absent
`libwestlake_html_compat.so` path, rolled back after the window.

**Caveat to verify in window 10:** if OH has *already* created `nweb_ns` in that process with a different `lib_path`,
`dlns_create` returns `EEXIST` and `dlns_get` gives OH's `nweb_ns` (whose search may not include `/data/local/tmp`); the
entry then falls back to placing the worker where that namespace can see it, or uses `dlopen_ns` of the worker by a path
the existing `nweb_ns` permits. The window-10 log (`dlns_get`/`create` return codes) settles which branch applies. For
route a proper, this is moot: the WebViewProvider calls `NWebHelper`, which manages `nweb_ns` itself — route a does not
create `nweb_ns`, it just has to reach `libarkweb_core_loader` (platformsdk, runtime-CL-visible) and call in; `NWebHelper`
then builds `nweb_ns` the permitted way.

**(B) is the fallback** if the target-name route has an unforeseen block: add a loader entry inside a DSO already in the
`default` ns (the bridge/runtime), which route a's WebViewProvider calls. That is a frozen-file change and is not needed
unless (A) fails.

## Why this is faithful, not a workaround

`nweb_ns` is OH's own designated ArkWeb namespace name, and the target-name branch is the platform's intended way to let
a web engine be loaded from an app context. Using it is copying OH's loader, not bypassing a boundary.

## Files

- `evidence/musl-permission-rule.txt` — the `dynlink.c` rule with line numbers.
- `evidence/namespaces-observed.txt` — namespaces in an appspawn-x child vs the permitted list.
- `evidence/open-site-scan-runtime-bridge.txt` — runtime/bridge open sites (all `caller-default`, no `dlns` site).
- `evidence/window9-permission-wall.txt` — the denial that motivated this.
- `results.json`.
