# Host transition: source triage, retained candidate unchanged

The visible development page is not evidence of a failed Toutiao launch. In the retained activation, the first host image contains exactly the title and text input defined by the legacy `Index.js`; a later sampled image is a real feed. Removing that page is a presentation change, not proof of faster Android startup. No device call, build, deployment, or runtime change was performed.

## Source chain

All paths, line ranges and whole-file SHA-256 values are in [source-index.json](source-index.json). `MAIN` means the main checkout, `VM_COPY` means `WORKSPACES/vm-copies/westlake-current`, and `ACTIVATION` means the private persistent window named in [results.json](results.json).

Revision 01 fixes the DIGEST citation to commit `e5cfcdfb3e5247a76d83f51cc388a44a895710b5`, blob `8b8619d01977844bf49222cddaa552aab4eb2d99`. These bytes exactly match the originally observed SHA. The checker reads that Git object and verifies both its SHA-256 and line 197, independently of subsequent working-tree additions. The other eleven source entries and the cited conclusion are unchanged. [Revision receipts](revision-01/results.json) retain the prior index/checker/manifest and demonstrate a local append fixture failing the old checker and passing the new one; MAIN was not edited.

1. The actual launcher record selects `org.westlake.imehost.EntryAbility`. Legacy `VM_COPY/apps/imehost/EntryAbility.js:19-28` loads `pages/Index`, sets the light background and records the main window. `Index.js:11-25` renders **Westlake IME host** and **Native OHOS keyboard control**. These match the inspected image. This is source/visual correspondence, **not byte-identical reconstruction of the installed HAP**.
2. The supplied 5cd control files are byte-matched against activation's before-supplement: `MAIN/benchmark/2026-10-12-snapshot-path/candidate/entry.sh:14-30` waits for the human foreground host before starting the guardian; `launch-common.sh:26-46` requires one visible imehost row and checks the parent environment's `WL_PARENT_ID`. `watchdog.sh:236-269` starts/reuses the parent and invokes `spawn.sh`, then verifies the child. These are exact archived component matches; the complete running guardian command/overlays are not independently reconstructed here.
3. `MAIN/sources/api-implementations/source-build-host/westlake-java/apps/imehost/Index.js:1-25` already contains the later empty black parent page; its `EntryAbility.js:24-28` uses a matching black background. Provenance is upstream `a2hlab/westlake@691433b967ba01365a382d30fbd820c1231c0811`, pinned by `java-source.lock.json`. This is an existing source-level solution to the development-page exposure. Its deployment/effectiveness on the retained candidate is **unknown**; the source delivery README expressly disclaims sealed-byte equivalence.
4. Neither inspected EntryAbility loads ART nor starts the Android child. Bypassing the OH host is not an established replacement: its live window is the Android parent-window prerequisite. No validated direct-Toutiao launcher shortcut was established in the bounded local source search.

## Actual timing (sampling, not first-frame latency)

Activation boot `13e5b7eb-5e98-40a8-9086-a25a4a32f2d6`: icon dispatch epoch `1792493310.602187`; quick capture brackets child `7669/b11062`, parent `5824`. The child AppSpawn log already occurs at epoch `1792493325.233`. At `1792493328.532077` (**+17.929890 s**) the inspected image is host-only. At `1792493391.590379` (**+80.988192 s**) the inspected image is a real feed. Thus child startup had begun while the host page remained visible. There is no continuous image series or first-present event here: exact first-feed latency and its decomposition are unknown. Do not attribute the entire interval to the one-second foreground poll. The next image at `1792493473.026655` is the lock screen, not another feed sample.

## Smallest reversible path

Propose a new isolated host-page revision reusing the already delivered empty-page implementation. Change only `Index.js` development controls and the corresponding `EntryAbility.js` background; preserve bundle/ability identity, loadContent path, lifecycle logging, main window, permissions, signing identity, app data, foreground and child guards. Do not import the later whole manifest/framework or bypass the host. This removes the explicit development UI but still shows a waiting background until Android presents.

The existing `westlake-java/tools/build_apps.py:35-52,59-89,121-125` provides `--only-host`, pinned V1 Restool 4.105 and API-20 ABC packaging. It produces an **unsigned** HAP; the adjacent manifest-tools signing recipe is separate. Neither was executed. Before implementation/build admission, bind the installed signed HAP/ABC/resources and signing/UID compatibility to the actual source, and preserve its exact rollback artifact. No claim that this recipe alone reconstructs today's installed HAP.

Installation can restart the host and change its WID. The documented failure in `MAIN/.octos/KNOWLEDGE-DIGEST.md:197` is Android children targeting a stale `WL_PARENT_ID` and remaining invisible. Therefore this is not automatically isolated from video operation. Current retained six-state restoration does not itself back up the HAP. Any future approval must explicitly cover host HAP rollback plus fresh host/parent/WID binding; the retained WID29 recovery is not a general HAP recovery tool.

## Validation boundary for a later approved task

- Source/package delta: only intended page and background; original app identity, native/runtime files and child-launch guards unchanged. Exact old signed HAP available; signature/UID/data preservation verified before installation.
- Normal icon, host-window creation, parent and child birth, first actual feed/frame: record separate timestamps. Measure the same endpoints before/after if claiming speed; a black page is not acceleration evidence.
- Check fresh WMS host WID against parent `WL_PARENT_ID`, child/window ownership, normal warm reentry, feed and the accepted video switch/pause/resume behavior. Do not ask for repeated per-clip audio confirmation.
- Roll back the host package through a separately reviewed path and re-establish matching live window/parent binding. No such operation is authorized or executed in this triage.

No new implementation is included. The short source review precedes any implementation. Spec checks are static provenance checks; human visual review remains explicit and does not become a performance or HAP deployment PASS.
