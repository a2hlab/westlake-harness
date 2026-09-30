spec: project
name: "Offline v3c candidate assembly"
---

## 约束

- No device I/O, locks, runtime implementation edits, source input writes or git metadata writes.
- Use the latest cx-t0 handoff: B87 base, retained liblog 8c81a937, CE runtime 9e14bf20, current networking host, old nativeloader.
- Package checks and recorded-state planning are not board validation or visual acceptance.
