spec: project
name: "BMS same-boot launch diagnosis"
---

## Intent

Locate the launch divergence between HelloWorld and Wikipedia on the assigned OH6.1 board.

## Constraints

- Use only 5ea34a4500000000000000001123012c with the cx-t0 board lock.
- Preserve boot and runtime generation throughout A/B; do not reinstall, reboot, or patch the runtime.
- Preserve raw logs and distinguish observation from inference; do not infer an absent short-lived process from a late snapshot.
