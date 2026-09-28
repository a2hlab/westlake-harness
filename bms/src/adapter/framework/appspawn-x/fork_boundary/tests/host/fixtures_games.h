#ifndef FIXTURES_GAMES_H
#define FIXTURES_GAMES_H

#include "spawn_oracle.h"

/* 10 target arm64 il2cpp games (data-model.md "Fixture: 10 个 arm64 il2cpp 目标游戏"),
 * sourced from 02d.APK_Flow's 20-package installability matrix (✅ ELIGIBLE + engine=il2cpp).
 * Only package/process identity is needed for this round's protocol tests — no real
 * APK bytes are required (see spec.md Clarifications). */
typedef struct {
    const char *label;       /* human-readable source label, for test output only */
    const char *bundle_name; /* package/process identity carried through the protocol */
} GameFixture;

#define GAME_FIXTURE_COUNT 10

extern const GameFixture kGameFixtures[GAME_FIXTURE_COUNT];

#endif /* FIXTURES_GAMES_H */
