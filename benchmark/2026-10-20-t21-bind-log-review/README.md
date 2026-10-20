# Offline T21 binding and operation reconciliation

The T20 candidate has not yet produced a reviewed live binding receipt. `reconcile.py` accepts **saved** fixed-range log bytes and before/after child maps; it never runs HDC, attaches, reads process memory or modifies a runtime. It extracts only strictly shaped `[WL-R20-*]` technical messages, preserving source byte offsets, lengths and hashes. Unrelated configuration/URLs are omitted.

```sh
python3 benchmark/2026-10-20-t21-bind-log-review/reconcile.py \
  --log "$FIXED_RANGE/selected.raw" --source-offset "$ORIGINAL_BYTE_OFFSET" \
  --maps-before "$READ/maps-before.stdout" --maps-after "$READ/maps-after.stdout" \
  --out "$READ/t20-log-reconciliation.json"
```

A `MATCH_OBSERVED_LAYOUT` result requires all three owner functions, both actual owner reference targets, seven provider functions, one successful context creation, exact known function offsets and matching executable mappings/inodes before and after. All provider records must select the reported provider base; identical files mapped twice are not conflated. Refusal, repeated/missing members, malformed log fragments or a changed mapping prevents that result. Operation counts and the first **observed** failing operation are limited to the supplied byte range, not a claim about a full run. Both original maps and log hashes are recorded. Six synthetic parser tests cover two instances sharing an inode, cross-instance mismatch, changed inode, truncation, refusal and nontechnical content exclusion; these are not device observations.

Minimal fresh evidence, collected only by the outer loop under its existing bounded window:

1. Bind boot, child PID/birth/UID/exe, parent identity/private namespace and holder before/after; retain the fixed-range transport framing and inode/range receipt. The tool cannot establish these from a map or log file alone.
2. Bind exact player, candidate shim `5cc23582…`, owner bridge `dca530…` and surface `8f1879…` actual file SHA/dev/inode. Require a single selected bridge instance. Record all surface instance mappings, not just the first match.
3. Independently read the exact player's two 8-byte GOT slots at **player bias + `0x472490` (lock)** and **+ `0x472760` (unlock)**. Expected candidate targets are **shim bias + `0x6430`** and **+ `0x6444`**, respectively. Source offsets come from the already reviewed exact player and final production-04 ELF. Pair logs do not replace this evidence. Do not use offsets with another player or candidate.
4. Cross-check logged owner Reference/Unreference targets against actual owner slots **bridge bias + `0x1740a0` / `0x173fc8`** and the selected surface instance. Seven typed function offsets are fixed in the tool from exact8f exports; they must agree with fresh mappings and the artifact receipt.
5. Read actual request/map/unmap/flush/retained results. A successful pair is still not a visual verdict: retain screenshot/timing evidence showing continuous content frames. User-confirmed T18 clip audio remains valid and separate. A failed/no-log binding is a finite result, not grounds for automatic retry.

Sources: `../2026-10-20-t20-provider-link-slice/provider-evidence.json`, `shim/pair.c`, final `production-04.json`; player slots from `../2026-10-19-toutiao-video-playback/static/r10-live-review/checkpoint-02/window-binding.json`. No production source, build artifact or previous evidence is changed by this package.
