#ifndef U12_MEDIA_PLATFORM_H
#define U12_MEDIA_PLATFORM_H

#include <stdint.h>
#include <sys/types.h>

#if defined(__APPLE__)
typedef off_t off64_t;
#endif

#define __INTRODUCED_IN(api)
#define __INTRODUCED_IN_32(api)
#define __INTRODUCED_IN_64(api)
#define __DEPRECATED_IN(api)
#define __BEGIN_DECLS
#define __END_DECLS

#endif
