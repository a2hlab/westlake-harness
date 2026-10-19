# R10 exact executor and reader handoff

This is an offline, UNAPPROVED successor. Executor changes are only the review sentinel, exact compat SHA and compat input directory. Reader changes are only compat SHA and input path. The checked-in differences and reverse comparison prove all other bytes, including run/player/media pins, three backups before first swap, four target CAS, partial rollback and original/current WID whole-file SHA sets, are unchanged.

Actual build receipt: `BASE20/r10-build-copy-02/build`, 16 stages rc0, full receipt inventory verified by the original `verify.py accept-build`. Exact output is `5f591f5ed92e608a622ab4b59bb2061a846600d0ac5e5d4698405e6301ac8c3c`. Independent ELF parsing confirmed mirror `0x1aac` and unique JUMP_SLOT vprint `0x3258`; these happen to equal r8. `build-review.json` binds every raw stage file SHA without exposing private host paths. Production build logs/artifact remain in the outer durable build directory; this delivery does not overwrite outer admission.

The outer must place that exact artifact at `candidate-r10/deploy-inputs/libopensles_android_compat.so` and independently admit a new window. This packet does not approve deployment or playback. The frozen executor refuses before argument processing, BMS import or device creation. A later approved successor must preserve this original.

Reproduce offline only:

```sh
python3 "$DEPLOYMENT/verify_delta.py" --source-repo "$MAIN"
python3 "$DEPLOYMENT/check_offline.py"
```

The second checker uses labelled synthetic fixture metadata and exact templates, evaluates real validation/generation blocks, and emits shell text without executing it. It covers 32 accepted rollback combinations, 11 foreign/tampered-plan refusals, three early refusals, backup ordering and immediate CAS. It does not prove remote filesystem operations by mock output. Existing missing-backup checks are inspected in the generated shell sequence.

Reader CLI retains the original arguments and identity gates. Its original result-only behavior is preserved: **outer must require both named `player_mirror_GOT` and `compat_vprint_GOT` checks to match plus completed final identity**. Its rc0 alone is not binding acceptance. Retain the original r9 paired network reader as well. Provider binding, effective video interaction, decoder outcome and audio remain unknown until actual evidence; 4096 attempts can still exhaust early and writes can perturb timing.
