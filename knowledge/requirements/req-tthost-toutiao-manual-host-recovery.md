---
kind: requirement
id: REQ-TTHOST
title: "Toutiao manual host recovery"
status: accepted
liveness: auto
tags: [toutiao, demo, lifecycle]
---

## Problem

The demo must open Toutiao through its desktop icon after startup and after an ordinary task dismissal. A live article process or newly created host is insufficient: the 2026-10-24 ordinary desktop reopen created host10486/window62 while child22035 survived, but all four sampled screens remained white.

## Requirements

[REQ-TTHOST-OPEN] On the designated demo board, an ordinary desktop icon click after system startup MUST display an operable Toutiao feed without a shell launch or operator recovery step.

[REQ-TTHOST-REOPEN] After ordinary Recent-task dismissal, a subsequent desktop icon click MUST restore an operable feed even when the previous article process survives its host window.

[REQ-TTHOST-PRESERVE] Recovery MUST preserve the verified same-host foreground/background, input, surface and video behavior; process liveness MUST NOT substitute for screenshots and manual UI operation.

[REQ-TTHOST-DELIVER] Changed implementation, source-to-artifact references, reproducible build recipes, validation evidence and API-table mappings MUST be available on the repository's actual mainline, master.

## Scenarios

Scenario: Startup from the desktop
  Given a rebooted demo board with the accepted runtime and usable network
  When the ordinary desktop icon is clicked
  Then the feed is visibly rendered and responds to normal touch without a shell launch

Scenario: Host replacement with surviving article process
  Given a visible feed and an ordinary task dismissal that destroys its host
  When the desktop icon is clicked and the host is recreated
  Then the feed becomes visible and operable rather than leaving the host background indefinitely white

Scenario: Ordinary background return
  Given an existing host and visible feed
  When Home is pressed and the desktop icon is clicked
  Then normal feed and video operation are retained without unnecessary producer replacement

## Dependencies

Frozen API behavior, exact deployment identity, a single board owner, rollback artifacts and source/build evidence remain required. Existing stopped actions are not reopened by this requirement.

## Source Trace

- User: "持续工作直到修复头条白屏"; "断电重启可以手点开"; "崩溃...下次打开又能打开头条信息流就行了".
- User explicitly authorized agent-driven software reboot for the current validation; software reboot evidence must not be labelled physical power interruption.
- benchmark/2026-10-24-recents-close-desktop-reopen/README.md records the ordinary close/reopen failure.
- benchmark/2026-10-24-existing-demo-reentry/final-v4/ records an earlier slow successful feed launch, not a reliability guarantee.

## Open Questions

- Whether native reconnection can retain the existing surface producer is under source review; do not prescribe a new window architecture before that result.
- Startup latency and repeated recovery still require actual measurements. A diagnostic milestone is not final acceptance.

## Next

Single exit: finalize bounded implementation contracts under specs/toutiao-host-window-recovery after the actual API and producer-lifecycle constraints are established.
