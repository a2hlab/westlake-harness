# WMC isolated baseline staging revision

The earlier plan treated incomplete historical dependency recording as a pre-experiment blocker. This revision permits a controlled attempt using the fixed existing SDK and explicitly identified nine snapshot headers. **Only local staging ran; no compilation, link, VM, device or network operation ran.** Output SHA remains the future reproduction criterion.

## Ready local output

`$DELIVERY/.private/staged-03/` is a completed isolated stage (`STAGED_NOT_BUILT`). It verifies111 link inputs,624 recorded dependencies including9 explicitly mapped snapshot headers, and8042 SDK file entries. Its `build/` directory is empty. The full SDK manifest SHA is `8912158bea2529cec351f3061e756fbd4509195358813f596eeddf7095ae4124`.

Exact future commands are already written:

- `mac-original-relink.argv.json`: original T29 ordered link inputs, pinned copied Mac tools, new `build/bridge-original-object.so`; expected `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`.
- `linux-compile.argv.json`: original385 arguments, both producer roots mapped into staged inputs, only object/dependency output paths redirected; expected object `f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed`.
- `mac-recompiled-relink.argv.json`: same link with exactly the WMC object and output changed; expected bridge b0e again.

`argv-preview.json` replaces this private stage path with `$STAGE` for public review. The original raw link argv/streams/rc and extracted compile argv are preserved in stage `records/`; original Ability38 artifacts/log/dependency files remain under `inputs/ORB_WS/out-ability38/native-policy/`. `records/mapping.json` records mappings; `records/header-mapping.json` records every snapshot source/hash/destination. This is not a claim that the9 headers already reproduce the historical object.

## Staging entry (does not build)

```sh
python3 "$DELIVERY/stage.py" \
  --repo "$T4" \
  --sdk "$HOME/.local/share/westlake/toutiao-resume-20261020/r10-local-toolchain/native" \
  --sdk-files "$DELIVERY/.private/sdk-files.json" \
  --out "$NEW_PRIVATE_STAGE"
```

`$T4` supplies the already indexed T18 archive/T29 original records; `$DELIVERY` is this new staging-01 directory. All parent preparation metadata hashes are checked through `input-pins.json`. An alternate `--archive` may select the same exact archive bytes. `--mac-sdk` can select another location only if all required bytes match the pins. No download occurs.

If the future Linux executor sees the tree at another absolute path, create a fresh stage with `--linux-stage-root <actual Linux-visible stage path>`; this only affects Linux argv. The successful local stage currently uses its local absolute path, whose Linux visibility has **not** been tested. Do not guess a VM mount. Source/include/prefix-map ordering is unchanged. `sys/types.h` remains an unchanged `-include` search operand; lack of historical cwd does not prohibit the experiment. Use an explicit fresh build cwd and record it, the environment and exact argv when execution is approved.

## Safety, input and tool handling

Only selected regular archive members are restored. All tar names are validated before extraction; traversal, absolute/backslash paths, duplicate names, symlinks, hardlinks and special files are rejected. No `extractall` is used. Output creation is exclusive; an existing output is refused, never cleaned or reused. SDK links must be relative and resolve inside the fixed SDK. Every restored/copied file is SHA/size checked. Original frozen trees are not modified.

The existing R10 Linux clang-15/lld bytes equal the original archived tools. The complete fixed SDK (sysroot/resources included) is staged, rather than pretending historical `-MMD` lists every system header. This does not claim complete host-OS provenance or a successful compile. Copied macOS clang++/ld.lld use `@loader_path/../lib`; the actual three SDK dependencies (`libc++.1.dylib`, `libc++abi.1.dylib`, `libxml2.2.14.0.dylib`) are pinned and copied to stage `lib/`. Existing system dylibs are normal host dependencies, not a reason for an OS-wide audit. `otool` reads are preserved; tools were not launched.

Future outer execution must create persistent per-step argv/cwd/environment/stdout/stderr/rc records **before/while running**, using the existing T29 raw recording pattern, with a new per-step log directory. Nonzero rc or mismatching object/bridge SHA is a retained experiment result to investigate; do not substitute the archived object and label it a reproduction. Candidate WMC is absent and no candidate build is prepared here.

## Actual local validation

- First staging attempt failed on SDK `lld` symlink vs archived regular-file representation; original partial stage, script and logs are preserved. Correction only retains an already restored regular file when bytes match the SDK pin; recorded in `retained-regular-sdk-links.json`.
- Final stage03 rc0, all stated inputs verified; no build outputs.
- Five safety tests rc0: traversal/absolute paths, tar links/special files, duplicates, valid paths, and hash-mismatch collision preserving existing bytes.
- Reusing the completed output refused with rc1; no overwrite.
- Compile argv equals the declared original mapping; include order and `-include sys/types.h` unchanged. The two relink arrays differ only in WMC/output.

The original preparation16-file packet is untouched. This revision's public manifest covers only new sidecars/scripts; private SDK/file/raw manifests remain at the exact indexed local paths for outer execution.
