# R15 duplicate-identity — itemized review (emphasised axis)

File under review: `provider_adapter.c` `5fc32ea5…`. All line numbers are that file unless noted.

## The net (three cooperating mechanisms)
1. **`by_identity(a,v,native)` (25-29)** returns `-1` the instant a live (`phase!=EMPTY`) record other
   than the first already holds the same buffer/native pointer — ambiguity is never resolved by
   "pick the first".
2. **`deny_identity(a,value,native,op)` (33-36)** poisons **every** live record holding the duplicate
   value (`deny()`→`suppressed++, adapter_error=-EPROTO, failed=1`) and returns `-EPROTO`.
3. **`collision(a,idx,native)` (37-41)** runs **under the lock, immediately after** a buffer/native is
   recorded (request:55, convert:78); if any *other* live record shares the value it marks **both**
   the other record and `idx` `uncertain=1, failed=1`.

Every op that can cause a lower side-effect is gated by one of: `by_identity`→`-1`→`deny_identity`
(handle:59-60, convert:73-74, map:84-85, unmap:96-97) or the `uncertain/failed` record gate
(handle:61, convert:75, map:86, unmap:98, flush:109, abort:119). So an ambiguous identity denies at
the *next* op before any lower call.

## Race analysis — the "publish then poison" window (CONDITION, not a bug)
Because `collision()` is retroactive, a `request`/`convert` can return `0` (publishing `*out`) a
moment before a competing thread creates the duplicate and poisons the record. Trace (two windows wA,
wB; buggy provider returns one buffer `b` to both):
- Thread A: reserve slotA, unlock, `p.request`→`b`. Relock, `rA.buffer=b`, `collision(A,0)` — if wB's
  buffer not yet set, **no hit** → A returns `0`, publishes `b`.
- Thread B: later `rB.buffer=b`, `collision(B,0)` sees `rA.buffer==b` → marks **both** `uncertain+failed`.
- Thread A's **next** op (`handle`/`convert`/`map`) now sees `by_identity(b)`→`-1` (two holders) **or**
  `r->uncertain` → denies **before dispatching** its lower call. No *new* lower op is dispatched on `b`.

**Precise guarantee (narrowed).** A lower op is dispatched only for an identity that is unique under
the lock at dispatch. Once a duplicate is detected (on return via `collision`, or at the next op via
`by_identity`→`-1`): bits are **not published**, and no **further** lower op (`map`/`unmap`/`abort`/
`flush`) is dispatched for the poisoned records — cleanup is suppressed and the slots are retained. It
is **NOT** true that "no lower side-effect ever occurs" or that "map is always caught": a lower call
**already in flight** for a then-unique identity **cannot be revoked** and completes. This is exactly
what **test_adapter.c:138 `duplicate-during-map-no-publish`** shows — window-0 is blocked **inside** the
`map` provider call (its `convert` already published native `&w0.n`, and the lower map **runs**);
window-1 then converts to the same native and poisons slot0; on resume window-0's `map` relocks,
re-reads `r->uncertain` (line 91), **refuses to publish bits** (`CHECK(w.rc!=0)`), and R14's resulting
unmap thunk denies (`!count(public.unmap) && !count(public.abort)`); window-1's own ops are gate-denied
before any further lower call. So the already-entered call is irrevocable, its result is discarded, and
all subsequent/new calls are refused.

## Collateral poison of an innocent in-flight window (CONDITION — contract-mandated)
test_adapter.c:134-137 (`duplicate-buffer`/`duplicate-native`): window-0 is fully, legitimately
locked; window-1's provider returns window-0's buffer/native. `collision` poisons **window-0 too**, so
window-0's later `r14_unlock` fails and its lower `unmap`/`abort` are suppressed (`duplicate-native`
asserts `ar.calls[R15_UNMAP].suppressed==1 && !raw_valid`). An innocent window therefore loses its
lower cleanup (a retained, un-reclaimed slot = a fail-closed *leak* on provider misbehaviour). This is
**mandated** by t10 "跨OH重复buffer/native身份拒绝发布并禁止猜测清理" — refusing to guess which window
owns a duplicated buffer is safer than a double-unmap/double-cancel. Correct, not a defect.

## Same-OH alias serialization is R14's, un-bypassed (CONDITION resolved)
The adapter keys records on the pointer R14 passes to `request`, which is the **already-unwrapped
`oh`** (R14 `window_module.c:70` passes `oh`). R14 rejects a second lock whose unwrapped `oh` matches
a live slot **before** calling the provider (`window_module.c:65`), so an alias never reaches the
adapter. Proven by test_adapter.c:131 `lock_w(e,10)==-EBUSY` with `!count(w10,"public.request")`. The
adapter adds per-record reservation **without** holding its mutex across the blocking provider call
(lock→reserve→unlock→`p.*`→relock), so a *distinct* window proceeds concurrently (`!lock_w(e,1)` in
the same test) — satisfying both "不得持全局锁跨阻塞provider调用" and "不绕过R14同OH别名互斥".

## Capacity
`request` (47-51) returns `-ENOSPC` under the lock **before** any provider call when all 8 slots are
`phase!=EMPTY`; `by_window` first returns `-EBUSY` for a re-request of the same window. Proven by
test_adapter.c:133 (`eight-retained-ninth-no-side-effect`): 8 failed+retained slots, 9th
`-ENOSPC` with `!count(w8/w9,"public.request")`.

## Bug table (duplicate-identity axis)
**none.**
