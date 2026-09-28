#pragma once
typedef struct AStatsEvent AStatsEvent;
inline AStatsEvent* AStatsEvent_obtain() { return nullptr; }
inline void AStatsEvent_setAtomId(AStatsEvent*, int) {}
inline void AStatsEvent_writeInt32(AStatsEvent*, int) {}
inline void AStatsEvent_writeInt64(AStatsEvent*, long) {}
inline void AStatsEvent_writeString(AStatsEvent*, const char*) {}
inline int AStatsEvent_write(AStatsEvent*) { return 0; }
inline void AStatsEvent_release(AStatsEvent*) {}
