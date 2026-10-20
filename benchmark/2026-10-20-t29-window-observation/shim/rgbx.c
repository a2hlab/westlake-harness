/* Android RGBX2 in an OH12 RGBA backing buffer. No allocator/provider calls. */
#include "rgbx.h"
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stddef.h>
static int layout(const struct r14_handle *h,const void *p){
 if(!h || !p || h->format!=12 || h->width<=0 || h->height<=0 ||
    h->width>INT32_MAX || h->height>INT32_MAX ||
    h->stride_bytes<=0 || h->size_bytes<=0 || h->stride_bytes%4 ||
    h->stride_bytes/4>INT32_MAX)return -EINVAL;
 if((uint64_t)h->width>SIZE_MAX/4 ||
    (uint64_t)h->stride_bytes>SIZE_MAX ||
    (uint64_t)h->size_bytes>SIZE_MAX ||
    (uint64_t)h->stride_bytes<(uint64_t)h->width*4 ||
    (uint64_t)h->height>SIZE_MAX/(uint64_t)h->stride_bytes ||
    (uint64_t)h->stride_bytes*(uint64_t)h->height>(uint64_t)h->size_bytes)return -EINVAL;
 return 0;
}
int r28_prepare(const struct r14_handle *h,struct r14_buffer *out){
 if(!out)return -EINVAL;
 int rc=layout(h,out->bits);if(rc)return rc;
 if(out->format!=1 || out->width!=h->width || out->height!=h->height ||
    (int64_t)out->stride*4!=h->stride_bytes)return -EINVAL;
 out->format=2;return 0;
}
int r28_opaque(const struct r14_handle *h,void *bits){
 int rc=layout(h,bits);if(rc)return rc;
 /* All checks precede the first byte. R14 COMPLETING exclusively owns bits.
  * RGB, row padding and bytes beyond the active rows remain unchanged. */
 unsigned char *p=bits;
 for(size_t y=0;y<(size_t)h->height;y++)
  for(size_t x=0;x<(size_t)h->width;x++)
   p[y*(size_t)h->stride_bytes+x*4+3]=255;
 return 0;
}
