#pragma once
typedef struct AStatsManager_PullAtomMetadata AStatsManager_PullAtomMetadata;
typedef struct AStatsEvent AStatsEvent;
typedef struct AStatsEventList AStatsEventList;
typedef int AStatsManager_PullAtomCallbackReturn;
#define AStatsManager_PULL_SUCCESS 0
typedef int (*AStatsManager_PullAtomCallback)(int32_t, AStatsEventList*, void*);
