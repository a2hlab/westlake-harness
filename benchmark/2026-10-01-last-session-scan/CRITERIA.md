# Last-session lookup scan: criteria before observation

Scope: the exact 66 first-attempt records selected by U7 formal-66; screenshot categories retain the outer signatures at 06:25:18, 06:33:44 and 06:39:59. Offline only. Raw logs may include other apps, reflected method names and duplicated stderr messages.

1. Bind package to its app PID using the existing first_fatal loader and scoring evidence. Count only executed events from those PIDs, through the signed t20 cutoff. Keep pre-click session initialization in that PID's session. Missing launch/log/PID is unknown, not zero sessions.
2. Count successful createSession events and distinct session IDs separately. Preserve the ordered oh_wm_set_last_session_local sequence. Deduplicate stderr mirrors, not repeated executions.
3. Associate BBQ.create VRI[Activity] with its buffer-queue identity, session attachment and later BBQ.update/getSurface events. Prefer explicit queue/session identifiers; otherwise same-PID/TID ordered association is provisional and must be labeled. Do not join unrelated threads or apps by nearest global line.
4. Record successful updates separately from getOhNativeWindow(sessionId=N) returned null and returning empty Surface. Record the last local session at each lookup; a null is evidence for the non-last-session mechanism only when its session differs from the then-last session. No log is not proof of success.
5. A null on the Activity actually intended to be on screen is a white-screen candidate, not proof of causation. A null limited to a positively identified background Activity is not an on-screen blocker. Foreground Activity identity needs explicit lifecycle/focus evidence or an outer Activity-level sign-off; the last-created session is not automatically foreground. Unknown foreground remains unknown even when the key is signed white or bright.
6. Exactly one observed session and complete launch/log evidence is outside the multi-session mechanism; any null there is a counterexample to the stronger claim that single-session lookup never fails, not hidden. Zero observed sessions is a coverage gap, not a negative control.
7. Pick three signed-bright, exactly-one-session, zero-null apps as negative controls. Retain every other signed-bright null as a counterexample to equating any null with white. Do not alter frozen scores or infer lighting from counts.

Output: 66-row machine-readable results and a Markdown table of key, session counts, null counts/Activity, signed visual state and conditional impact, with raw file/line/hash receipts. Preserve all per-queue event sequences and attribution uncertainty.

## Outer extension at 08:00 (before extended scan)

Count `getOhNativeWindow: unknown sessionId` and GLSurfaceView's `IllegalArgumentException` containing `valid Surface` separately for every key, including single-session keys. The same PID/time/execution rules apply. Preserve whether an unknown-session message precedes that session's successful creation or occurs later, and the then-last session. Unknown-session is not automatically a BBQ.update null, nor proof of a failed EGL call. An IAE is a caught GL-thread observation, not automatically a process-terminal event. Keep zero counts for Mindustry, PPSSPP, Mobile or x if their bound logs do not contain the signature.
