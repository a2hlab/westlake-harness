# Exact Ability38 source → object → deployed bridge identity

The previously missing mechanical provenance edge is now verified from the original local archive. No compiler, device command or runtime modification was used.

| Edge | Independently checked evidence |
|---|---|
| Original producer record | `ORB_WS/out-ability38/native-policy/artifacts.json`, SHA `5db328cf263ba1575401d096b5afe3f5cecb3298066b14811a85a3d6570e223b` |
| Compile source | Record source SHA and actual archived source both `1844e81ba3183430040717e3fca7bffadf0d9a9724e55a543da1480aaf667a5e`; tracked Ability38 snapshot equal |
| Compile output | Original compile-window-manager argv selects that source and exact object; rc0. Object record and archived object both `f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed` |
| T29 actual link | Original13-bridge-candidate argv SHA `e960b1d1c12776cf6deceac1792abb0a60f3fb43d1de74eb935b88bd14d619cb`, includes that exact object once; original/public rc0 and input pin match |
| Final ELF | Actual T29 bridge.so and output receipt both `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4` |

Original archive: `$T4/benchmark/2026-10-20-t18-build-evidence/source-closure/.private/archive-02/window.tar.gz`. Original T29 run: `$T4/benchmark/2026-10-20-t29-window-observation/.private/production-01`. The archive-member and byte checks are performed by the replay command, not inferred from matching filenames. This is original record/byte verification, not a fresh reproducibility build. The final ELF hash is the independently supplied deployed identity.

The exact source is `sources/api-implementations/bridge-d4fa-source-snapshot/ability38/framework/window/jni/oh_window_manager_client.cpp`: lines173–187 implement the positive parent-window ID cache; lines1787–1790 use its result for SetParentId and SetParentPersistentId. These facts now belong to the recorded source/object/link chain rather than only an older base-layer candidate. They still do not prove current session53 state, whether any later lifecycle path ran, or a white-screen root cause.

Replay from any checkout (explicit repository roots; read-only):

```sh
python3 "$REVIEW/check_binding.py" --main "$MAIN" --t4 "$T4"
```

Actual replay returned0; raw argv/stdout/stderr/receipt remain in `.private/check.*`. The checker refuses mismatched source, object, producer record, actual link argv, compile/link rc or ELF.

One separately authorized SSH source-read attempt returned255 with Operation not permitted and empty stdout; original `.private/ssh.*` remains unchanged. No retry or alternative entry occurred. Dump investigation is closed here at outer's direction: outer obtained the public `-w` help/data, and CC owns its interpretation. No dump-parameter claim or session-parent inference is added by this delivery.
