spec: project
name: "Offline native namespace-edge scanning"
---

## 约束

- Only extend the offline scanner, its tests and evidence; never deploy or modify U10.1/T8 binaries.
- Preserve the existing scan()/findings() consumers and seven known-answer tests.
- Normalize namespace names using dlns_init/get and translate child parameters across one direct caller only.
- Control-flow reachability is a syntactic may-path proof, not value-sensitive execution or live namespace ownership.
- Unknown expressions, missing ELF inputs and indirect calls remain explicit coverage limits.
