# R15 failure-cleanup — itemized review (emphasised axis)

Lines in `provider_adapter.c` `5fc32ea5…`; R14 lines in `candidate-r14-offline/window_module.c`
`1f42a393…`. Cross-checked against `static/r14-provider-next-review` ELF evidence.

## The lever: `uncertain` vs `failed`
- `failed=1` — R14 slot unusable + retained; a **clean** lower cleanup is still allowed.
- `uncertain=1` — a lower side-effect may have occurred and cleanup is unsafe; the **only** flag that
  makes `unmap`/`abort` thunks **deny the lower call**.
`abort_buffer`'s gate (119) checks `r->uncertain` and **not** `r->failed` — deliberately, so a
cleanly-failed buffer (e.g. handle-NULL at 68 sets `failed` only) is returned to the provider, while a
poisoned one is not. `deny()` (31) always sets `failed` (conservative). This asymmetry is correct.

## R14 fail-path it mirrors (window_module.c:86-92)
`fail:` → `if(mapped){unmap}` (87) → `if(buffer && (!mapped || !unmap_rc)){abort}` (89). So R14 unmaps
only if map returned rc0, and aborts only if no map happened or the unmap succeeded. The adapter drives
these two predicates via `uncertain`.

## Case-by-case (public.* = lower provider call; from the two-layer journal)
1. **Map rc0 + all-1s sentinel** (map:88-93; test failures kind=2, lines 105-109/107).
   `bits==(void*)UINTPTR_MAX` → `uncertain=1,failed=1` (89); `phase=MAPPED` (rc0, so R14 `mapped=1`);
   `*out` **not** published (91), synthetic `adapter_error=-EPROTO` (92); **public rc0 preserved**
   (93). R14 calls unmap thunk → `r->uncertain` gate (98) → **deny**, no lower unmap, returns
   `-EPROTO`. R14 `!r.unmap_rc` false → **no abort**, retain FAILED. Journal asserts
   `!public.unmap && !public.abort`, `R15_UNMAP.suppressed==1 && !raw_valid`,
   `r.unmap_called && r.unmap_rc && !r.abort_called`. ✓ fail-closed.
2. **Map rc0 + plain NULL / 2nd-internal-Map-fail** (kind=1,3; 105-109/108). Not the sentinel →
   `uncertain` **not** set; normal path: unmap thunk calls lower **once** (99), on rc0 → `phase=UNMAPPED`;
   R14 then aborts, abort thunk proceeds (not uncertain, phase≠MAPPED) → lower abort once. Journal:
   `public.unmap==1 && public.abort==1 && internal.Map==2` (no 3rd internal Map / no retry). ✓ matches
   "rc0/NULL普通路径只调用一次公共Unmap，依真实rc决定是否允许公共Abort".
3. **Map nonzero rc + non-NULL addr** (map:88-93; test `map-error-nonnull`, line 111).
   rc≠0 → `uncertain=1,failed=1`; `phase` stays CONVERTED; `*out` NULL; **public rc preserved**
   (returns 50007000). R14 `mapped=0` → no unmap, then abort → abort thunk `r->uncertain` gate →
   **deny** lower CancelBuffer. Journal: `!public.unmap && !public.abort`, `R15_MAP.raw_rc==50007000
   && R15_ABORT.suppressed==1`. ✓ "Map非零...相应Abort thunk抑制下层并返回合成错误".
4. **Request error / contradiction** (request:55; test `request-error-owned-fence` 104,
   `request-conversion-failure-*` 112-115). `rc || !b || fd<-1 || collision` → `uncertain+failed`;
   fence still forwarded (`*fence=fd`, 56) so R14 owns+closes it (`close.fence==1`). Any later abort
   → `r->uncertain` gate → suppressed. ✓ "request非零或矛盾输出...相应Abort抑制".
5. **Public Abort never counted as release** (abort_buffer:116-121). Sets `r->failed=1` **before** the
   lower call, records `raw_rc` only, **never `memset`s** — so even `abort=0` leaves the slot
   retained+failed. ✓ matches R14 which keeps FAILED after Abort=0, and t10 "公共Abort=0不记成底层释放".
6. **Unmap lower failure** (unmap:101). rc≠0 → `failed+uncertain`; R14 (`r.unmap_rc` set) skips
   flush/abort and retains. Proven by `unmap-flush-error-0/1` (116-120). ✓.
7. **Flush failure** (flush:112-113). rc≠0 → `failed+uncertain`, record **retained** (no `memset`);
   `unmap-flush-error-2` asserts `public.flush==1` then retained. ✓.
8. **Reclaim only on full success** (flush:113). `memset(r,0,sizeof(*r))` runs **only** when
   `!rc && !r->uncertain` (the `else if(r->uncertain)` catches a collision set during the unlocked
   lower flush). ✓ "只有正常成功flush才可回收".

## Signed widening does not hide a failed map
`handle` writes `*out` only on `p && !uncertain` (68-69); on any deny `*out` stays the entry `memset`
zero (59). A map that failed earlier poisons the record, so `map`/`unmap`/`flush` all deny downstream.

## Bug table (failure-cleanup axis)
**none.**
