#ifndef WESTLAKE_R20_ENTRY_H
#define WESTLAKE_R20_ENTRY_H
#include "provider_adapter.h"
#ifdef R20_INTERNAL
#define R20_API __attribute__((visibility("hidden")))
#else
#define R20_API __attribute__((visibility("default")))
#endif
/* Linkable integration slice only. No Android symbol interposition or resolver.
 * Owner supplies a trusted unwrap capability. It must only return a borrowed OH
 * window whose valid lifetime covers the entire lock -> unlock/retained period.
 * No arbitrary-pointer validation is provided. Caller externally serializes
 * create/destroy, quiesces ALL API calls and prevents new calls before destroy.
 * One context per ownership domain, never two contexts for the same OH window.
 */
struct r20_owner { void *ctx; int (*unwrap)(void *,const void *,OHNativeWindow **); };
struct r20_context;
R20_API int r20_create(const struct r15_provider *,const struct r20_owner *,struct r20_context **);
R20_API int r20_lock(struct r20_context *,const void *,struct r14_buffer *,struct r14_rect *,struct r14_report *);
R20_API int r20_unlock(struct r20_context *,const void *,struct r14_report *);
R20_API int r20_report(struct r20_context *,const void *,struct r14_report *);
/* On failure, context and uncertain ownership remain retained; no force reset.
 * Destroys R14 first, then R15. On success caller must discard the pointer. */
R20_API int r20_destroy(struct r20_context *);
#endif
