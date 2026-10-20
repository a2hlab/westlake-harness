# T25 geometry — offline implementation and exact T23 relink

The prior design did not implement geometry. This independent translation unit adds the trusted wrapper-to-OH boundary without changing any T20/T23 source or object. T23's 121 geometry errors remain a candidate hypothesis, not proof of the black-video cause. **Status: OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED.** Actual runtime geometry entry/winner and video remain unknown.

`geometry.c` takes one extra owner reference, unwraps once, passes original width/height to HandleOpt opcode0, and only after success sends opcode3 for positive formats. Mapping is Android 1/2/3/4/YV12 → OH12/11/13/3/11; other positive values pass unchanged. Release runs exactly once after every acquired exit. The first real opcode error is preserved; release failure after otherwise successful operations returns -EPROTO. Reports have separate called flags: a zero field on an uncalled operation is not success.

The production resolver uses existing owner/shim handles with RTLD_NOLOAD. Exact owner get/acquire/release offsets and readable Reference/Unreference slots must match dependency-scope resolutions and one surface base; HandleOpt must be that instance's offset0x68c10. Before any wrapper operation, the exact player caller path and its three readable ELF slots (lock0x472490, unlock0x472760, geometry0x472048) must point to this shim's entries. This rejects mixed765 lock routing; it does not update the old private format ring or support raw-OH pointers. The caller must already own a valid bridge window reference and externally serialize geometry/lock/destroy. This is not arbitrary-pointer validation. Outer still must pin the actual mapped files and observe the runtime route before device acceptance.

## Actual offline evidence

- 29 real-C host cases (including six format mappings) passed. Loader identities are fixtures, but the production resolver, `admitted_caller`, and `dispatch` execute. After binding only the ops counting seam is replaced. Wrong caller/lock/unlock/geometry slots refuse with zero owner/OH calls; the admitted route records AGDFR and balances references.
- Seven malformed build-receipt fixtures rejected; two Rust selectors passed.
- Existing T23 23 cases and T20 11 cases passed without source changes.
- check_frozen: 8 entries / 30 checked / 0 violations.
- Original T23 objects relink to byte-identical `a9abaf09ce020c45dea5a30d1030a8ae7f939a2f4434cd6ff3aec53cfc9726b6` (77,792 bytes).
- Candidate: `2a867f78905bdc37020bec36c951f628c6393456a1770514c1d73f974fd3d5bc` (82,112 bytes). Old77 full export/version tuples remain; only `ANativeWindow_setBuffersGeometry@@LIBC` is added. NEEDED unchanged, no TEXTREL, exact HWUI and player consumer ABI checks passed.
- Production01 compiled/linked successfully but its verifier expected an unversioned export and rejected it. Original logs remain. Production02 validates the exact @@LIBC version; no ABI gate was relaxed.
- Strict lifecycle returned **rc1: 7 pass, 1 human PendingReview, 0 failed**. The entire spec is not marked complete. See `evidence/lifecycle-summary.json`; original full output remains private.

## Reproduction

Use existing pinned production02 inputs; no tool installation, new SDK, device or shared-file modifications are needed. Set `MAIN`, `OH_NATIVE`, `T23_BUILD`, `HWUI_SO`, `PLAYER_SO`, and a fresh persistent `OUT`. `T23_BUILD` is the existing `t23-egl-build/production-02` directory. The build verifies all original46 input hashes and the original object hashes, then pins the new compile dependencies (63 total input records). `--path-map OLD=NEW` is available when restoring the same inputs elsewhere; bytes must still match. Preview is default.

```sh
python3 benchmark/2026-10-20-t25-geometry/check.py
python3 benchmark/2026-10-20-t25-geometry/build.py \
  --repo "$MAIN" --sdk "$OH_NATIVE" --t23-build "$T23_BUILD" \
  --consumer "$HWUI_SO" --player "$PLAYER_SO" --out "$OUT" --execute
python3 benchmark/2026-10-20-t25-geometry/check_receipt.py "$OUT"
T25_BUILD_OUT="$OUT" cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test toutiao_t25_geometry -- --nocapture
```

`production-02.json` is a sanitized projection of the actual receipt. `evidence/public-source-index.json` binds every projection to original bytes. `private-raw-index.json` indexes the original source snapshots, full raw argv/stdout/stderr/rc, compiled objects and all attempts. Producer artifact: `$T25_DIR/.private/production-02/candidate.so`. Large/private original inputs remain in the existing persistent T23 input locations; no remote archive or upload is claimed by this packet. `$T25_DIR` is this benchmark directory in the producer lane.

`BLUEPRINT.md` and `review-response/` retain the supplied pre-implementation design/evidence. `origin-pins.json` records those originals; the task spec now explicitly permits offline implementation/builds only. `donor-pins.json` records reused source identity. No deployment authorization, runtime test, media result or whole-spec completion follows from this build.

Public path projection uses longest path first; [alias-map.json](alias-map.json) defines each alias. Original T23 producer paths remain `$WORKSPACES/westlake-harness-video-plan/...`, never an undefined `$MAIN-video-plan` alias. Four overlapping-prefix cases were checked; this projection-only correction did not rebuild or change the candidate/private logs.
