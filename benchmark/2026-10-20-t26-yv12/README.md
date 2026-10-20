# T26 YV12 presentation: source, build and artifact index

The player requests YV12, while the previous lock result exposed a packed RGB format. T26 retains the logical YV12 layout in a bounded scratch buffer and converts it to physical OH12 / RGBA8888 before Unmap/Flush. Other RGB requests keep the previous path. T27 records the actual buffer/config and selected EGL create pointer in the same candidate.

| What to inspect | Repository source or evidence |
|---|---|
| Layout, allocation limits, cache and RGBA conversion | [yv12.c](yv12.c), [yv12.h](yv12.h) |
| Real lock/unlock/geometry and EGL integration | [derived/](derived/), [derive_glue.py](derive_glue.py), [derivation-pins.json](derivation-pins.json) |
| Same-provider SDK getter adapter | [observation.c](observation.c), [observation.h](observation.h) |
| Bounded observer implementation | [T27 observer and tests](../2026-10-20-t27-buffer-observation/README.md) |
| Exact combined source selection | [joint-glue.json](joint-glue.json), [production landing manifest](production-landing-manifest.json) |
| Actual build and ABI results | [production-02](production-02/README.md), [receipt](production-02/receipt.json), [source pins](production-02/source-index.json), [raw command index](production-02/raw-index.json) |
| Complete private inputs, source snapshots and original execution logs | [joint production archive](../2026-10-20-t26-joint-production-archive/README.md), [remote verification](../2026-10-20-t26-joint-production-archive/remote-success.json) |
| Separate deployment transaction | [deployment data](../2026-10-20-t26-shim-deployment/README.md) |

## Build on the host

Run from the repository root with Python 3 and clang available. Choose new, persistent output directories; the builders refuse to overwrite an existing directory. These commands run host tests and do not operate a device.

```sh
REPO="$(git rev-parse --show-toplevel)"
T26="$REPO/benchmark/2026-10-20-t26-yv12"
T27="$REPO/benchmark/2026-10-20-t27-buffer-observation"
python3 "$T26/build_host.py" --source-repo "$REPO" \
  --out "$HOME/.local/share/westlake/replay-t26-host-01"
python3 "$T26/build_joint_host.py" --source-repo "$REPO" --observer "$T27" \
  --out "$HOME/.local/share/westlake/replay-t26-t27-host-01"
```

## Build the OH shared library

[build.py](build.py) is the combined production recipe. It first reproduces the accepted T25 baseline, then compiles ten translation units with `WL_T27_OBSERVER`, `_GNU_SOURCE=1` and the actual OH SDK headers, replaces seven inherited objects, and checks unchanged nonempty versioned exports and dependencies.

A git clone contains the implementation and recipe. The pinned SDK/toolchain, original T25 build receipt/link inputs and exact HWUI/player binaries are private build inputs: restore them from the verified archive before running this recipe. Use the archived private path-to-input mappings; the public receipt uses aliases. `--path-map OLD=NEW` is repeatable when restoring those inputs under different roots. A new-machine rebuild has not been claimed by these existing receipts.

With `OH_SDK` set to the restored native SDK root, `T25_BUILD` to the accepted raw T25 production directory, `HWUI_SO` and `PLAYER_SO` to the pinned consumer files, and `BUILD_OUT` to a new persistent directory:

```sh
python3 "$T26/build.py" --repo "$REPO" --sdk "$OH_SDK" \
  --t25-build "$T25_BUILD" --t27 "$T27" --joint-glue "$T26/joint-glue.json" \
  --consumer "$HWUI_SO" --player "$PLAYER_SO" --out "$BUILD_OUT" \
  --execute
# Add each required --path-map OLD=NEW before --execute when paths differ.
```

The expected candidate is **96,680 bytes**, SHA256 `fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9`; baseline SHA256 is `2a867f78905bdc37020bec36c951f628c6393456a1770514c1d73f974fd3d5bc`. The private joint archive is **69,494,594 bytes**, SHA256 `5d16542a056fca0b2ac102743b1669236de4b4670f35c88924e81247c80ed515`, at `HW248_ARTIFACT_ROOT/t26-t27-joint-production-20261020-fc58cec5/production.tar.gz`. Its remote receipt verifies all 1,793 members and includes all 116 actual production inputs.

The production records retain their original offline/pending states. The later archive receipt closes remote persistence; it does not rewrite earlier records. Build, archive and host success do not establish current device binding, video playback or a seal decision.
