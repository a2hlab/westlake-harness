---
kind: requirement
id: REQ-GENSHIN-STATIC
title: "Genshin existing-input static intake"
status: proposed
liveness: auto
tags: [genshin, static, evidence]
---

## Problem

The user requests Genshin work after the current demo task. No exact Genshin package, resource completeness or playable OH result has been established by this contract. BoatAttack evidence can guide investigation but cannot establish another game's compatibility.

## Requirements

[REQ-GENSHIN-STATIC-INPUT] The intake MUST identify lawfully available existing base APK, splits and associated assets by actual metadata, provenance and full SHA256, or report MISSING/PARTIAL/UNKNOWN without acquiring new inputs.

[REQ-GENSHIN-STATIC-MAP] The intake MUST record version, ABI, SDK, JNI and graphics observations with exact input references and distinguish static candidates from runtime failures and verified BoatAttack behavior.

[REQ-GENSHIN-STATIC-HOLD] The intake MUST preserve all devices, including 61b, and exclude downloads, login, execution of app code, deployment and runtime changes.

## Source Trace

- User's deferred Genshin task, routed by the outer coordinator on 2026-10-21 after T34 W04 closure; this requirement authorizes only the bounded offline intake described by the associated task.
- specs/demo-baseline/t2b-boatattack.spec.md: BoatAttack-specific generation, rendering and touch evidence must not be generalized to Genshin.
- AGENTS.md: existing verified implementation first; exact object and namespace evidence; static import counts are not observed fatal failures.

## Next

Outer review of specs/genshin-static-intake/t1-bounded-static-intake.spec.md precedes dispatch. Requirement governance remains proposed. Any implementation or device experiment requires a separate evidence-driven task.
