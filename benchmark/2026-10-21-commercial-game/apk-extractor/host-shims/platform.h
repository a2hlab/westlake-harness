#pragma once
#ifdef __APPLE__
inline int sched_getcpu(){return 0;} // unused: harness uses nonparallel Open only
#endif
