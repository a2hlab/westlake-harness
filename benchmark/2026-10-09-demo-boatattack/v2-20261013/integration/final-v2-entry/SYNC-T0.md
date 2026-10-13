# Immediate narrow-review dependencies

Old provider freeze 3e7c4224 remains immutable and is blocked for execution by your UID finding. The separate `../final-v2-candidate-r2/` now parses dedicated original BMS package/UID receipts bracketed by actual boot reads, checks transport + remote rc + serial + ordered times + package/app/user100 UID agreement, and re-reads that identity through the original transport before both core fresh rounds and rollback. No receipt gets an invented UID. Tests 9/9 offline; exact pins are in identity-interface.json and the separate final-v2-candidate-r2/freeze.json.

61b preinstall actual state: BMS absent; APK and signal-box absent; unity1e446/il2cpp5855 present and both outside319. `prepare_boat.py` reuses the pinned original BMS Board + missing-only install_one, backs up/checks both stock files, rejects existing drift, then creates only the controlled empty signal target with the historical 644/0/0/data_app_el1_file policy. It stops at fresh-capture-required; no preinstall capture is promoted to complete.

Exact stage graph:
1. explicit preinstall request + fixed8dc APK -> actual BMS registration/empty placeholder -> STOP for fresh identity/metadata capture.
2. compile disabled Boat r2 plan -> independent review/outer authorization.
3. explicit `demo_restore.sh --v2-recipe`: original r5 live same-board selfcheck OR original r2 restore + r3 exact487 receipt admission -> Boat standard-argv provider. Any nonzero or incomplete receipt stops. Current 5cd-only r4b directory executable is NOT invoked on61b; all three existing RouteB directories are required by the Boat preflight.
4. outer snapshot/sepolicy -> separately authorized single reboot -> current READY56/BOUND7 + WID observation -> original r5 selfcheck against full new v2 realization. No bare reboot/reinstall from old demo_seal_61b.py.
5. complete128 driver: reuse `integration/fresh128-handoff-r2/run_candidate_post_reboot.py` (7cc72083…) and original board_run / collect / regress_vs_signoff / missing-record STOP / special slots. Its current imported BMS `identity-r4/candidate_identity.py` has hard-coded SPARE5ea and typed RouteB absence at lines58/98, so it is NOT61b ready. Required narrow sibling delta: 61b proof compiler+identity reader covering original319 with exactly4 replacements, Boat18 targets, preserved actual RouteB487+HAP; replace only imported/pinned candidate hook and new output paths in the full driver. Keep Mac controller/Orb Reader, pre-lock/after-lock/before-unlock identity hooks and all128 membership. Neither 5ea absence nor old 61b install receipts can supply current128 identity.
6. actual128 comparison + Boat/RouteB visual slots -> outer signature. Pending results stay pending.

Mechanical inventory is in expected-union.json: 811->824 files, 129->130 APK/HAP records, 954 unique expected objects; 13 added files include all3 private targets, plus5 changed old files. Not940 and not a live PASS.

No HERDR_ENV or direct T0 pane is available in this session; this exact file is the local review handoff, not a claim that a lane message was delivered. Root may relay it immediately for independent review of these frozen candidates.
