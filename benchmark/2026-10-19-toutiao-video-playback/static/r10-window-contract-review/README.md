# Exact window contract review

Only redirecting the player's lock/unlock imports to libandroid765 is not yet a complete repair. Its width, height, geometry and buffer-request paths pass the supplied pointer directly to OH. Exact HWUI a11c9154 `ANativeWindow_fromSurface` instead preserves or creates an adapter wrapper. Whether this dependency function is the actual inner `dlsym` winner remains unknown.

The exact deployed bridge d4fa implements `oh_anw_get_oh` at ELF 0x125a00: it checks 0x5f776e64 at +0 and 0x414e5731 at +0xc8, then returns +0xc0. The existing 64-byte historical head fails the first check and does not cover the latter fields. It cannot prove a current AdapterAnw, a valid raw OH window or corruption. A latest render pointer with lifetime provenance is required. No old address should be reused blindly.

The exact libandroid765 helper at 0x37d4 stores a bridge handle at 0xd720 and calls dlsym at 0x3814 on every request. That handle is not a cached fromSurface function. Exact bridge dynamic symbols have no fromSurface/getFormat definition and DT_NEEDED includes libhwui, supporting a dependency-resolution possibility, not the actual namespace winner. Native-ready=1 only establishes the initialization flag, not geometry or buffer success.

## Minimal caller-directed reuse

After proving the wrapper, reuse the existing unwrap contract at the player's OH-consuming boundary for geometry and the paired buffer lock/flush path. Preserve the original wrapper for acquire/release and paired lock bookkeeping. Preserve format, stride, fence, map/unmap and flush semantics. Do not substitute a raw OH pointer into wrapper release or treat unwrap failure as proof that the input is a valid raw OH window. Avoid global replacement of shared WebView libandroid/shim implementations; non-player consumers must retain their current bindings.

Existing native691 `webview_bionic_shim.c:3962` illustrates a wrapper-aware software-buffer path; this is a reuse reference, not proof of deployed bytes or live success. `libandroid_webview_shim.c:877` documents wrapper ownership, but its getFormat differs from exact765. Related-source `oh_anativewindow_shim.cpp:813` also adds directPathLive absent from exact d4fa. The exact ELF checks take precedence. Full paths, hashes and source lines are pinned in source-index.json.

## Smallest missing observation

Bind the current render/fromSurface object to the current child, inspect +0/+c0/+c8 using the exact bridge layout, and establish the actual same-namespace inner dlsym winner. The examined helper has no persistent winner slot, so a guessed extra GOT read cannot prove it. Existing resolver/caller evidence or an exact loaded dependency lookup is needed. No new device command, probe or build is supplied here. The existing six OH table addresses and native_ready do not replace this evidence.

commands.json and the two stdout/stderr pairs retain actual local LLVM rc0 inspection. results.json separates static facts from runtime unknowns. The original providers, candidate packets, API observations and device state were not changed.
