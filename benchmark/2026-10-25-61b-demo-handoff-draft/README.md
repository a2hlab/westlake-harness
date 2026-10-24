# T147 61b demo handoff draft and read-only delivery checker

Offline draft; no device action, no runtime tool change, no new spec.

- `OPERATIONS-DRAFT.zh-CN.md`: short Chinese operating notes. It separates the three openings verified by T136 v9
  (`execute-20261025-041851-b503ee/result.json`, `21a9c90d…`, outer-reviewed, rolled back by design) from items in
  progress (T141 two software boots) and pending items (speaker/video audio, physical power cycle). First open showed
  white first and a feed at about 60 s (no feed by 120 s counts as failed; recovery from white is not promised),
  re-entry about 5 s; these are this round's observations, not guarantees. T136 v9 verified a swipe in firstopen and
  samehost and an article click only in recreated. Candidate retention is decided only by the
  final T141 result/receipt.
- `check_delivery.py`: reads only manifest-listed files, verifies SHA-256 and the T141 handoff chain (boot1 result and
  boot2 outer receipt pin the handoff SHA; boot2 `boots[0]` equals handoff `candidate_boot`), classifies the T141 state
  from original fields, lists recorded review receipts and pending items. It does not inspect images, does not treat a
  script exit 0 as image review, and always reports `sealed: false`.
- `manifest.template.json`: input template. `tests/test_check_delivery.py`: 10 synthetic cases.

Run: `python3 tests/test_check_delivery.py`.
