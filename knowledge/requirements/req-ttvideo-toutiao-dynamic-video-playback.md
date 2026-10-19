---
kind: requirement
id: REQ-TTVIDEO
title: "Toutiao dynamic video playback"
status: proposed
liveness: auto
tags: [toutiao, media, demo]
---

## Problem

The user requests playable Toutiao video on the OH demo while the higher-priority icon-reentry task continues. Historical feed/cover screenshots do not prove video playback. Current playback route and first failing API remain unverified.

## Requirements

[REQ-TTVIDEO-TRACE] The investigation MUST bind the active APK, runtime, board, player, video surface and first failing operation to current evidence before choosing a repair.

[REQ-TTVIDEO-PLAY] Toutiao MUST play a known non-silent video with changing content frames and audible corresponding audio, pause, resume and return to feed without requiring shell launch.

[REQ-TTVIDEO-DELIVERY] Each changed public API MUST map to repository implementation, reproducible build instructions and separately scoped deployment and app evidence in the API atlas.

[REQ-TTVIDEO-ISOLATION] Video work MUST preserve the icon-reentry priority, single board owner, rollback baseline and frozen behavior, and exclude random-crash root-cause changes.

## Scenarios

Scenario: Observable video lifecycle
  Given a current board identity and a reachable non-silent video
  When the user opens video, pauses, resumes and returns to feed
  Then ordered content frames and audio show playback, pause and resume and the feed is visible after exit

Scenario: Missing service or evidence
  Given a network refusal or absent current runtime identity
  When playback is investigated
  Then the missing observation is recorded and neither bridge failure nor playback success is inferred

## Dependencies

The existing Toutiao icon-reentry operation owns 61b until its window is released. The video contracts provide independent offline work first.

## Source Trace

- User request, 2026-10-19: "用 /octoloop 继续执行任务 ... 用agent-spec规划 再加一个任务 处理好头条的视频播放问题".
- User scope: do not diagnose Toutiao random crashes; restore manual icon reentry first.
- benchmark/2026-09-28-toutiao-video-playback/README.md: historical frozen-cover observations, not current-generation proof.

## Open Questions

- Which player and output route are active in the reconnected device's exact APK/runtime? Resolved by t1, not guessed here.

## Next

Single exit: execute specs/toutiao-video-playback/t1-static-evidence.spec.md after outer review; t2 and t3 remain dependency-gated. Governance remains proposed pending the outer's requirement acceptance.
