spec: project
name: "U10 shared native compatibility entries"
---

## 约束

- Offline only; no board operations or push.
- Preserve aa7e77f943ab deployed compat exports and common function call sets.
- Use the thirty source files pinned by the v3a ROUTE_A_INPUTS receipt, not a nearby source tree.
- Reuse the existing real abort owner; never introduce a second abort-message state.
- Missing namespace semantics must fail explicitly, not silently become ordinary dlopen.
