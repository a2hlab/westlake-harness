# Connectivity boot-extension fallback audit (#88)

The proposed shortcut confused two runtime generations and treated a secondary image as an independent extension. The three nominated VM compilers are **OAT 247 / image 118**; the resident R155 package is **OAT 230 / image 108**. Their former use on the same physical board does not establish compatibility. No compiler was built, no image was generated, and this task made no board writes.

The fallback is no longer required for the connectivity service wall: cc-wiki reported the runtime-JAR `OnlineConnectivityManager` subclass working at 19:16 on September 29. Its `getActiveNetwork()` was called by Wikipedia and the `onGoOffline` fatal exception disappeared. Wikipedia then failed at `WikiSite.forLanguageCode`; this is **not** a claim that Wikipedia lit or that real networking works. This lane did not independently replay cc-wiki's run. See `results.json` for the run identity and verification levels.

## (a) Existing compiler audit

The following paths under the VM workspace `~/a2hlab/ws/` all hash to `8f9592174aa9d3f8b8f7e0d2879d15c6407e3c2f9f839346b8a8523c4434c7e3`:

- `out-aot42/tools/dex2oat`
- `out/host-tools/host/objects/bin/dex2oat`
- `out.75d82d5/host-tools/host/objects/bin/dex2oat`

`ImageHeader::kImageVersion` contains `31 31 38 00` (`118\0`); `OatHeader::CheckOatVersion` compares `32 34 37 00` (`247\0`). Evidence: [ELF constants](vm-art-format-versions.json), [version-check instructions](vm-oat-version-disasm.txt). The small [ELF reader](read_art_versions.py) reads named data symbols without executing the compiler; a missing constant in a stripped binary is **unknown**, not a mismatch.

The package's nine OAT files contain `oat\n230\0`, and its nine ART files contain `art\n108\0`: [OAT headers](oat-headers.json), [image headers](image-headers.json). This audit used the immutable local `westlake-generation-v3a-74d1d6d4-r8b` package, rather than disturbing cc-wiki's live board.

The current `boot.oat` embeds the original command and compiler path:

```
/opt/build-trees/aosp-arm64-d600/out/host/linux-x86/bin/dex2oat64
```

The [full original command](original-boot-command.txt) compiled all nine input jars in one invocation. That path was absent in the bounded hw248 lookup; a depth-eight scan below `/opt/build-trees` found no `dex2oat64*` file. This is not a claim that no copy exists anywhere.

Other existing AOSP14 candidates were found and are retained in `results.json`: `/a2hlab/work/issue-4/dex2oat64` (24ef24fd), the historical no-Baker/SS compiler (db463e76), and a later `image_writer.cc` patch variant (6936a27f). The issue-4 directory also contains an exact R155 `libart-d600.so` (59e1bb45), but colocation is not proof of a matching compiler. Eastlake receipts describe compiler closure and full boot builds, not a proven R155-compatible single-component replacement. Their resident compatibility remains **unverified**; further investigation stopped after the runtime alternative succeeded.

## (b) Can only the mainline component be replaced?

Not by the proposed command against this existing primary image. `boot.art` declares **9 components** and a **163,917,824-byte reservation**. `boot-adapter-mainline-stubs.art` declares zero components, zero reservation, and zero parent-image fields. It is a secondary member of that same image group, not an independent extension. Its `image_size` field is 256,148 bytes; that field is not the on-disk file size.

AOSP14 dex2oat supports extensions, but requires the compiled DEX files to be the **suffix** of the runtime boot classpath and requires a matching image for every preceding DEX. See the [source excerpt and SHA](extension-source-evidence.txt), `dex2oat.cc:1574–1624`. Here mainline is entry 7 of 9, followed by framework and adapter-framework. Reusing the current nine-component primary does not establish a new six-component prefix or remove the old mainline classes. A replacement must also handle its OAT/VDEX and downstream references/checksums. No header editing or checksum bypass was attempted.

This does not prove that every partial rebuild is impossible. It establishes that file-level splitting alone does **not** justify this particular drop-in. A correctly matched prefix/suffix image design would need separate validation. The cited real-work `gen_boot_image.sh` is a full nine-input recipe defaulting to ARM32, not an already validated ARM64 single-component recipe.

## Disposition and verification

Per the prior instruction to use the runtime subclass first and omit #88 if it succeeds, this fallback closes as **wontdo**, with the evidence retained for future boot-image work. No v3b image package was produced.

`agent-spec lifecycle` for the shared B11 contract returned exit 1: all four selectors matched zero tests and were **Skip**, not Pass (`lifecycle.json`). No specification was changed. The evidence-only report was checked for valid JSON and header/version consistency; these checks do not establish app acceptance or compiler/runtime compatibility.
