# T30 actual design review, r2

The strict resource-free predicate in CC design `e3af2364e1` matches the contract. Three corrections are required before claiming integration: `A` is owner acquire rather than Abort; the existing three-layer completion is sequential rather than atomic; and the fixture must compile the complete derived R14 implementation with real R26, entry and production pair, not only a values-only recovery model.

Actual production sources and SHA pins are in `design-review-r2.json`. The publicly stored R14/R26 sources match the private fixed-prefix copies and the production input receipt. The pair must come from `production-01/derived/pair.c`, which contains the new bridge owner offsets.

On extra-owner release failure the existing pair reports `-EPROTO` after R14 and R26 have already completed; raw Request and release results remain separately observable. This is not successful reference balance or a three-layer rollback. Keep that limitation explicit without adding an unrequested transaction or poisoning another concurrent call by wrapper identity. No build or device operation ran; final implementation and real-function tests remain pending.
