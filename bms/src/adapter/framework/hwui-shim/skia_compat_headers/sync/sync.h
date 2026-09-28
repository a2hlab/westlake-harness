#ifndef SYNC_SYNC_H_STUB
#define SYNC_SYNC_H_STUB
// Minimal stub for sync/sync.h — fence sync wait

#ifdef __cplusplus
extern "C" {
#endif

int sync_wait(int fd, int timeout);
int sync_merge(const char* name, int fd1, int fd2);
int sync_file_info_free(void* info);

#ifdef __cplusplus
}
#endif

#endif
