# T27 buffer observer

[observer.c](observer.c) and [observer.h](observer.h) implement bounded CPU-native, Android-output, import-config and actual-create observations. Records go to the existing stderr; absent getters leave metadata UNKNOWN. The actual selected EGL create pointer is called once and its return is reused.

The same-provider getter resolution and typed SDK adapter are in [T26 observation.c](../2026-10-20-t26-yv12/observation.c). The actual insertion points are in T26's derived window/CPU and EGL sources. [T26 source and build instructions](../2026-10-20-t26-yv12/README.md) give the host commands, combined OH production recipe, exact `fc58cec5` artifact and complete private archive. The observer is linked into that shared library; it is not a separate deployment.

For the standalone observer host check, run `python3 benchmark/2026-10-20-t27-buffer-observation/check.py` from the repository root. [RECEIPTS.md](RECEIPTS.md), [receipt.json](receipt.json) and [raw-index.txt](raw-index.txt) preserve the original host evidence. [production-02](../2026-10-20-t26-yv12/production-02/README.md) records the combined build. Host metadata fixtures, source review and offline ELF checks do not establish runtime getter binding or video success.
