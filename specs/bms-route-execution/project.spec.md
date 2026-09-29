spec: project
name: "OH6.1 BMS execution evidence"
---

## Intent

Execute campaign item 23 after the three-board HelloWorld and ZigZag baseline is accepted.

## Constraints

- Preserve original APK bytes, per-board ownership, unique run IDs, and every failed attempt.
- Target only the three assigned OH6.1 serials; stop on lost lock, transport, or changed boot.
- Keep installation, BMS registration, desktop click, process observations and visual verdict separate.
- No flashing, runtime replacement, automatic LIT verdict, or remote push.
