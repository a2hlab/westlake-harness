# APK native extraction exception source

The API table previously pointed only at an installer provenance report. This bundle provides the two actual candidate C++ files, both original patches, and the unmodified historical build script as evidence. The files were extracted from the original 478,511,698-byte archive, SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`; the mutable unpacked base installer is deliberately not used. Apache-2.0 copyright/license notices remain in both original C++ files.

The full native build closure remains in that SHA-pinned archive (its durable location and compiler SHA are in `source.lock.json`). Obtain it from `$LAB_HOME/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz` on the configured archive host, or use the matching `$WORKSPACES/oh61-bms-kit-b79-r3-final.tar.gz` copy. The archive includes Ninja files, source/header inputs, reused objects and toolchain. Linux x86-64, Python 3.12+, `/usr/bin/ccache`, and the compiler's runtime libraries are required.

```sh
python3 sources/api-implementations/JAVA-042-installer/build.py --archive "$ARCHIVE" --check-only
python3 sources/api-implementations/JAVA-042-installer/build.py --archive "$ARCHIVE" --out "$NEW_SCRATCH"
```

The new entry verifies source and full archive SHA, extracts a new isolated kit, verifies compiler/source bytes, touches the two production source inputs to require actual recompilation, and runs the original Ninja targets. It captures separate stdout/stderr and actual return code. It does not run the historical machine-specific shell file. This delivery only exercised source/archive validation and syntax; no fresh native build or historical binary equality is asserted. A failed build must remain failed even if old archive outputs exist.
