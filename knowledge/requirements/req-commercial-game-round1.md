---
kind: requirement
id: REQ-COMMERCIAL-GAME
title: "Commercial Android game compatibility campaign"
status: proposed
liveness: auto
---

## Problem

The user has started the next commercial-game round after the scoped 61b video seal. Genshin is the previously named target. The earlier local intake found no named package in its limited scope; remote stores and actual package manifests remain unsearched.

## Requirements

[REQ-COMMERCIAL-GAME-INPUT] The campaign MUST identify the exact package and resources before predicting compatibility, preserving original command receipts and distinguishing missing searched inputs from inaccessible or unsearched locations.

[REQ-COMMERCIAL-GAME-REUSE] The campaign MUST distinguish reusable public runtime mechanisms from BoatAttack-specific patches, and bind proposed work to exact inputs and observed blockers when available.

[REQ-COMMERCIAL-GAME-DEMO] The campaign MUST preserve 61b's retained demo and require a fresh target, board lock and recovery plan before any later spare-board experiment.

## Source Trace

- User: "下一步搞个原神上去看看，有一个开源赛艇游戏作为底子".
- User after the video seal: "ok 下一轮做个商业化游戏吧".
- benchmark/2026-10-21-genshin-static-intake/README.md: bounded local MISSING, not global absence.
- benchmark/2026-10-21-t34-demo61b-video/window-05-public/final-signoff.json: retained demo scope and limitations.
