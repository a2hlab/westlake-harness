# Source addendum: NO_BUFFER can be transient; recovery is conditional

The outer channel fetched four CPP files with rc0. All four text SHA256 values were independently verified before saving the exact Apache-licensed source bytes under [sources/](sources/). The earlier lane SSH rc255 and its original report remain unchanged. See [provenance.json](provenance.json) for raw outer receipt hashes and source identities.

**T30's narrow hypothesis is supported:** on the ordinary queue path, a request can fail with40601000 without permanently disconnecting the producer or assigning it a new buffer. A later normal lock/request can succeed after queue progress. This supports allowing the next normal request after releasing only the adapter's failed-attempt reservation; it does **not** prove that this window will recover, justify a busy retry loop, or establish the original live queue condition.

## All explicit NO_BUFFER returns in the four retrieved files

[return-sites.json](return-sites.json) enumerates all15 exact `return GSERROR_NO_BUFFER;` statements (14 BufferQueue,1 ProducerSurface). This is exhaustive for these four files, not for external callbacks, allocation/map implementations or the entire OH source tree.

| Source and original line | Condition / relevance |
|---|---|
|buffer_queue.cpp:158|PopFromFreeListLocked finds no matching usable free buffer and either the free list is empty, capacity is available (new allocation should be tried), or its only entry is the held last-flushed buffer. Internal sentinel; **not always a failed public request**.|
|:181|PopFromDirtyListLocked has no dirty entry. Used by nonblocking request and consumer acquire.|
|:366|Blocking reuse wakes/times out, still cannot pop a usable free entry and effective capacity remains full.|
|:382|Nonblocking reuse cannot pop a dirty entry.|
|:417|Listener-sequence/fence request cannot obtain a usable free entry; ordinary RequestBuffer uses the default false mode.|
|:543|Listener-sequence/fence reuse needs reallocation; puts the entry back on freeList then refuses.|
|:585|Listener-sequence/fence reuse needs new/cache-clean/consumer-attached/preallocated buffer information; returns the entry to RELEASED/freeList then refuses.|
|:974,:986|Timestamp-aware consumer AcquireBuffer sees no dirty entry, before or after dropping/releasing frames; not the producer request site.|
|:2593,:2597|GetFrontDesiredPresentTimeStamp has no dirty entry or no matching cached entry.|
|:2799,:2809,:2823|AcquireLppBuffer: fence unavailable, no new update, or sequence absent from cache.|
|producer_surface.cpp:829|OnBufferReleasedWithSequenceAndFence callback cannot find its producer cache entry; not the ordinary RequestBuffer return site.|

The retrieved BufferQueueProducer and BufferClientProducer CPPs contain no literal NO_BUFFER return statement. They propagate results. BufferQueue's simple AcquireBuffer also propagates the dirty-list sentinel (`:931–958`), and block-mode reuse can propagate the free-list sentinel at`:368`, without another literal return.

## Ordinary request paths and retry mechanics

`buffer_queue.cpp:387–440` first checks consumer status/listener and request configuration, then tries a free buffer. At full **effective capacity** (`GetUsedSize() >= bufferQueueSize_ - detachReserveSlotNum_`), it selects blocking or nonblocking reuse. `GetUsedSize():121–124` is cache size, not a count of actively owned buffers; a full cache can still succeed by reusing a free buffer. With capacity available, the request allocates a new buffer (`:334–348`). Explicit allocation or map failure is translated to UNKNOWN in`:1281–1328`, not directly to40601000.

- **Blocking (`:350–369`):** `wait_for(config.timeout, WaitForCondition)` checks free-buffer availability, available capacity, or status change. Its boolean result is not used to classify the error. The subsequent state decides: consumer gone gives NO_CONSUMER; usable free entry gives reuse; otherwise NO_BUFFER. Therefore40601000 alone does not prove a timeout.
- **Additional retry-relevant edge:** if capacity becomes available during the wait but there is still no free buffer, PopFromFreeListLocked returns NO_BUFFER and`:368` propagates it. The *next* normal RequestBuffer can reach SetupNewBufferLocked and allocate. The same call does not loop back to allocation.
- **Nonblocking (`:371–385`):** at full effective capacity it reuses the oldest dirty/flushed entry if one exists; otherwise returns NO_BUFFER. No wait or persistent failure flag is installed in these failure branches.
- **Progress sources:** CancelBufferLocked`:602–625` marks a valid requested/attached entry RELEASED, adds it to freeList and notifies waiters. ReleaseBufferLocked`:1235–1278` does likewise for a consumer-acquired/attached buffer (or deletes a pending-deletion entry). ReleaseLastFlushedBuffer`:807–820` removes the held-last-flushed exclusion and notifies. Queue growth`:1659–1682` can create allocation capacity. These are existing operations, **not proposed new repair actions**.

Queue-full *condition* in ordinary RequestBuffer can yield NO_BUFFER. The separate error `SURFACE_ERROR_BUFFER_QUEUE_FULL` appears in attach/preallocation paths (`:1470,:2710,:2722`); do not substitute that enum for the observed40601000. If no consumer releases/cancels/progresses, repeated calls can continue to fail indefinitely. Clearing the adapter's failed reservation does not manufacture an OH buffer or reconnect a dead queue.

The delegator route (`:433–438`, helper`:221–246`) forwards DequeueBuffer/Map errors; those implementations are outside the four files. Reuse and setup also call external functions. Accordingly this inventory does not exclude externally propagated40601000 or assert that the ordinary queue route was the live winner.

## Connection state, deployed ELF correspondence and limits

`buffer_queue_producer.cpp:1289–1302` calls Connect before RequestBuffer, sets `retval.isConnected=true` once connected, then requests from the queue. `:1712–1757` shows same-PID Connect may succeed again; different PID yields41206000, strict-disconnected yields41211000. Non-strict Disconnect clears connectedPid then CleanCache. Thus a connected producer can return NO_BUFFER. This is compatible with transient retry; it does not identify a new server generation after the observed TextureView reference exchange.

The fetched `producer_surface.cpp:123–151` matches the **checked control-flow features** of deployed libsurface SHA8f1879f82a307d3a95555067575132918a05244fbdeee1c2f2db37834a58f4a3: lower virtual request at0x6e0c0; retained status; special NO_CONSUMER cleanup; reply `isConnected` clears local disconnected flag at0x6e124; return at0x6e1bc. Its log is source line148, also encoded by the exact ELF. The fetched `buffer_client_producer.cpp:96–139` matches SendRequest→ReadInt32→error ReadBool→return at the previously disassembled0x331fc/0x33210/0x33344. Existing disconnect disassembly is consistent with the fetched connection handling. See the prior packet's exact LLVM records.

This is **localized semantic correspondence, not source-to-binary reproduction**. No source commit/build receipt proves these four files produced that deployed ELF. The server BufferQueue implementation and its live process were not matched to an ELF in this review. Consequently neither branch coverage nor live queue status can be backfilled from these sources.

For T30, preserve real40601000/adapter failure and distinguish `no buffer obtained` from partial ownership. Permit the next application-driven lock only when the failed attempt's local reservations/references have been resolved under the existing ownership rules. Do not Flush/Cancel a nonexistent buffer, erase unrelated live entries, change timeout/connection/provider/format, or report the initial failure as success. Actual recovery needs a later real request success and observed output; it remains unproven here. CC owns implementation; this addendum changes no code.
