spec: project
name: "B6 R155 static parity study"
---

## Intent
Compare the six immutable local ELF artifacts assigned by board item 53. Keep static evidence distinct from runtime causality and deliver files for outer-loop commit.

## Decisions
- Use the installed OH LLVM tools, SHA-256 identities and reproducible offline analysis.
- No device commands or modifications to input artifacts.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-b6-static-diff/**
- specs/b6-static-diff/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No device execution, input binary edits, git commit or push.
