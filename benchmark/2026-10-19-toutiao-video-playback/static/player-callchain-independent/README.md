# Independent review of player window call-chain evidence

**Partial acceptance: exact local call/field relationships are supported; full lifecycle, once-only assignment, runtime identity and unconditional constructor-to-lock provenance are not established.** The reviewed CC README is the rev2 byte snapshot identified in `results.json`; later rev3 edits are not silently covered by this review.

The five original CC files are **complete `procedure_pseudo_code` Evidence envelopes**, not complete `analyze_function` dossiers. Each envelope is JSON-equal to its record in the unmodified 122-record exported bundle, its full SHA256/size matches `extract-index.json`, and its subject SHA is `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`. The local ELF independently hashes to that SHA, size **4662040 bytes**. Original bundle SHA is `5a2016fa4e494145deed1941ce08b116be51fcc1938f3bca05d26c670a1d9e49`.

No new REA analysis was performed. Five function ranges were obtained from existing same-subject body metadata in that bundle, then independently disassembled with LLVM: **4104 bytes / 1026 instructions**. Seven 16-byte import stubs and the existing relocation table were checked to bind external-call labels without assuming Ghidra names. All tool receipts are rc0. No device operation, build or runtime change occurred.

## Original and derived evidence

- CC's original exported bundle, extracted complete envelopes and index remain unchanged under `$HOME/.local/share/westlake/window-callchain-A-rea-raw-20261020/`.
- Our original LLVM stdout/stderr/receipts, exact input hash, derived range metadata and the reviewed README/manifest byte snapshots are durable under `$HOME/.local/share/westlake/player-callchain-independent-20261020/`.
- `source-index.json` indexes both locations using full SHA256 and byte counts. `reviewed-pseudocode.txt` is a whitespace-trimmed projection of existing envelopes, not manufactured raw Evidence. `llvm-bodies.txt` and `llvm-import-binding.txt` alias only the local ELF pathname.
- All PCs below are **ELF VAs**; existing Ghidra addresses have `+0x100000` image bias. Neither is a process address. LLVM labels the stripped text ranges using a nearby exported symbol; that label is not the function's real name. We use the independently hashed instruction PCs and bundle body ranges.

## Supported statements and required limits

| Function | Exact independent evidence | Accepted scope |
|---|---|---|
| ctor, ELF `0x1c7628`, 324 bytes | `0x1c767c` zeros `this+0xe0`; `0x1c76dc` loads `*surface`; non-null path calls fromSurface PLT at `0x1c7714`; `0x1c7718` stores returned x0 to `this+0xe0`; nonzero result calls init at `0x1c7724` | This constructor initializes that field to zero and conditionally assigns the fromSurface result. There are two explicit field write sites, not one lifetime write. Base/helper calls are outside the reviewed bodies. |
| init, ELF `0x1c77e8`, 276 bytes | `0x1c7804/0x1c780c/0x1c781c` read `this+0xe0`; calls getWidth/getHeight/getFormat at `0x1c7808/0x1c7818/0x1c7828`; width/height results stored at `this+0x14/+0x18` | Native getter inputs come from this field. The getFormat return is not directly saved as the logged format: both logging branches call unreviewed helper ELF `0x1c79bc`. This does not prove live w0/h0/format-1 values or their cause. |
| dtor, ELF `0x1c7b60`, 192 bytes | `0x1c7bd4` calls virtual slot `+0x68`; `0x1c7bdc` calls helper `0x1c7c20`, followed by other cleanup calls | The destructor body delegates cleanup. It has no explicit `+0xe0` clear or direct ANativeWindow_release call. A claim that these helpers clear/release the field needs their exact evidence; it is not supplied by this body alone. |
| removeWindow, ELF `0x1c7460`, 312 bytes | `0x1c7498` reads second argument object's `+0xe0`; non-null branch calls helper `0x1c85c8`; null branch traverses entries and may call `0x1c86e4` | Reads the field and manipulates an associated container through helpers. No explicit store to that object's `+0xe0` exists in this reviewed body. It is not proof of native-window release or field clearing. |
| drawPicture, ELF `0x1f977c`, 3000 bytes | `0x1f9ae0` saves render object's `+0x80` into x23; `0x1f9aec` loads x0 from saved object `+0xe0`; `0x1f9af0` calls lock PLT with stack output buffer and null dirty rect | Lock's **local input load** is proved. Unlock paths `0x1f9f44`, `0x1fa240`, `0x1fa30c` and geometry path `0x1f9f94` reload that field of the saved object. Reloading the same address does not establish the same pointer value across time or exclude helper/concurrent writes. |

The five functions do not exhaust assignments to render `+0x80` or show that every such object was constructed by this exact constructor. The constructor's field source and draw's matching field offset form a **conditional structural source relation**. They are not proof that an arbitrary observed lock input equals a particular earlier fromSurface return. Constructor-instance assignment, intervening writes and lifetime remain unknown.

Likewise, no exhaustive `+0xe0` writer inventory or full call-graph side-effect analysis was performed. The reviewed README's scope downgrade is appropriate; its “Full lifecycle”, “write (once)” and “clear/destroy” headings should be replaced with the exact limited observations above so they do not contradict that downgrade. A once-only or no-setSurface-rewrite assertion is not accepted.

## Geometry has two distinct sources

Draw's entry calls second-argument virtual slot `+0x48` with property IDs `0x0f` and `0x10` (`0x1f97c4`, `0x1f97e0`), storing results at render `+0xa8/+0xac`. Calling this second argument a decoded frame is a contextual interpretation; the reviewed body proves the property reads and stores.

The actual `ANativeWindow_setBuffersGeometry` call at `0x1f9fa4` instead loads width/height/format from render `+0x190/+0x194/+0x1d8` (`0x1f9f98..0x1f9fa0`). Other paths call the window object's virtual slots `+0x18/+0x10`, then unreviewed helpers `0x1f7de4` and `0x1f7f88`. Those can participate in size preparation; their semantics were not expanded here. Therefore **entry frame-property dimensions must not be equated with final geometry dimensions**, and window-derived geometry cannot be ruled out from these five packages.

## External call names, not runtime winners

| Imported name | PLT ELF VA | Exact JUMP_SLOT address |
|---|---:|---:|
| ANativeWindow_fromSurface | `0x88160` | `0x472688` |
| ANativeWindow_getWidth | `0x86af0` | `0x471b50` |
| ANativeWindow_getHeight | `0x87070` | `0x471e10` |
| ANativeWindow_getFormat | `0x86710` | `0x471960` |
| ANativeWindow_lock | `0x87d70` | `0x472490` |
| ANativeWindow_unlockAndPost | `0x88310` | `0x472760` |
| ANativeWindow_setBuffersGeometry | `0x874e0` | `0x472048` |

Each stub loads through the listed address, whose exact ELF relocation names the import. This independently supports the call labels. It does not identify which loaded library/namespace ultimately satisfies the import or the libandroid bridge's inner dlsym. Claims about libandroid/libhwui/libsurface winners or AdapterAnw conformity were not independently re-audited by this player-only review.

## Review disposition

Accept the five envelopes as original exported evidence and the local instructions/call names above. Require the five scope corrections recorded as F1–F5 in `results.json`. Keep full lifecycle, constructor-instance linkage, runtime pointer equality, helper side effects, actual geometry and playback unknown. A later CC revision can be checked against these concrete statements without rerunning REA. No deployable candidate or relaxed runtime admission follows from this review.
