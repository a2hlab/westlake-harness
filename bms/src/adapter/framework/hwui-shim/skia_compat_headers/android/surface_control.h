#ifndef ANDROID_SURFACE_CONTROL_H_STUB
#define ANDROID_SURFACE_CONTROL_H_STUB
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

typedef void* ASurfaceControl;
typedef void* ASurfaceTransaction;
typedef struct ASurfaceTransactionStats ASurfaceTransactionStats;
// ASurfaceControlStats is an alias for ASurfaceTransactionStats (M14+ rename)
typedef ASurfaceTransactionStats ASurfaceControlStats;
typedef void (*ASurfaceTransaction_OnComplete)(void* context, ASurfaceTransactionStats* stats);

ASurfaceControl ASurfaceControl_createFromWindow(struct ANativeWindow*, const char*);
void ASurfaceControl_acquire(ASurfaceControl);
void ASurfaceControl_release(ASurfaceControl);
ASurfaceTransaction ASurfaceTransaction_create();
void ASurfaceTransaction_delete(ASurfaceTransaction);
void ASurfaceTransaction_apply(ASurfaceTransaction);
void ASurfaceTransaction_setOnComplete(ASurfaceTransaction, void*, ASurfaceTransaction_OnComplete);

#ifdef __cplusplus
}
#endif

#endif
