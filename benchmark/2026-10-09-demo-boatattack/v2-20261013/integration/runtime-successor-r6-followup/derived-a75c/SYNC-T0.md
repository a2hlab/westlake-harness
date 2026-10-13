# T0 handoff — isolated geometry candidate

Delivery: local handoff for root relay; no lane_send was executed (HERDR_ENV unavailable).

The 947 compiled TU is `benchmark/2026-10-13-popup-geometry-reuse/evidence/source-pair/source947.cpp` in t0, SHA `280a36f2000924cecc05feb60ca49d1c2a0fc72a660e02cd7488ad2dedfd2506`.
At BBQ_nativeUpdate line 602, both main/ViewRoot and dedicated SurfaceView reach the dimensioned setter. Existing classification is at 576, dedicated child resolution at 578–590. Separate policy using successful child resolution, not just the name: a SurfaceView can fall back to main. Preserve requested geometry for the actual dedicated child; test the historical main/ViewRoot compatibility policy separately. No popup type exists in OhBlastBufferQueue; requested aspect alone is not a popup identifier.

Coverage required: nativeGetSurface lazy path 635–644; non-mutating seed 1227 and fromSurface 1264; width-zero preservation in setBuffersGeometry 1324; EGL queried-size reapply and uninitialized fallback at 1429–1441. Retain M1 owner resolution and all API/linkfix behavior. ADC's stale seed log does not mean it writes geometry.

Counterexample: successful W3 PID10322 set BOTH main and dedicated child to 1920x1200 (original-cadence/hilog-stream.txt lines 3214, 3354–3355, 3380). A blanket change of all main surfaces therefore changes successful Boat behavior too; candidate sufficiency needs real images/input, not the static branch alone. BMS DropCount actual relayout is 1079x1260; use actual Seal/StudyTracker/DropCount and ClipboardEditor/LifeCounter controls.

Root's new same-board experiment rejects stock187+ADC: actual buffer1200x1920 vs default/bounds1920x1200; inputs0. Evidence: main `outer/r5-experiment-main-r4/run/boat/{record.json,surface-node.txt,child-view.json,final.jpeg}`. This does not prove every 947 change is required.

Full pinned evidence: sibling `geometry-surfaceview-static/results.json` and README. No new compile or device call by t4.
