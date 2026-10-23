# T95B — progress into render-submission logs; exact stage times unknown

Verified4MiB SHA `2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6`,50,179 lines and exact prior128KiB prefix. The old partial line1583 is now complete. Actual extractor rc0; no raw log copied publicly.

| Original line | Narrow observed progress | Timestamp/TID limitation |
|---|---|---|
|2009 /2036|Platform JNI_OnLoad entry / draw-interface registration|No explicit clock or TID; not a complete Chromium load timing pair|
|4259 /4327|MainActivity session-create entry / session31 Foreground return0|No explicit clock or TID|
|5023|Class-verification message|Explicit17:22:10, PID6291/TID6311; not a rendering timestamp|
|5485 /5868|RS transaction posted / UI-thread transaction flush record|No numeric TID or timestamp; UI-thread wording is only the logged description|
|6945 /6965|First matching swapBuffers ENTRY / WESTLAKE-SWAP rc=1 in this prefix|Evidence of rendering-submission progress, not visible contents or first-frame time|
|7152 /7171 /8868|Second session-create entry / session34 Foreground return0 / later transaction flush|No explicit clock or TID|

After the old boundary,15 explicit wall-clock anchors exist, only one on6311; the last other-thread anchor is17:22:25 at line34517. There are11,586 complete6311 now/TID records; unit/domain remain unknown and no conversion is performed. Results retain only first/last plus neighboring numeric anchors around12 selected stage lines. Neighbors describe file order, not synchronized timing bounds: interleaving/buffering prevents assigning them to untimed stages.

The fragment still ends mid-record at line50179 (TOUCH21-POLL), excluded from complete-counter counts. No content::Start match establishes the first T92 marker here. MainActivity posting, session operations and successful swap return do not establish completed onCreate, first visible frame or feed. No concrete slow-stage duration or optimization is proven; no network/fault/exit/memory/T96 analysis was performed.

Reproduce `extract_extended.py --input <private extended head.stdout> --old-prefix <private128KiB head.stdout> --output <new results path>`. Raw argv/start/end/rc/stdout/stderr are in `.private/`, pinned by raw-index.json. Device/REA/deployment/Git actions zero; original T95 review unchanged.
