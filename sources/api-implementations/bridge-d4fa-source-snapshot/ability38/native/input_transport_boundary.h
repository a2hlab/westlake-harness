#pragma once
#include <stdint.h>
struct WlTouchPointer { int32_t id; int32_t tool; float x,y,pressure; };
extern "C" {
#pragma GCC visibility push(default)
void* wl_input_publisher_create(int fd);
void wl_input_publisher_destroy(void*);
int wl_input_publish_motion(void*,uint32_t,int32_t,int32_t,int32_t,int64_t,int64_t,const WlTouchPointer*,uint32_t);
int wl_input_publish_key(void*,uint32_t,int32_t,int32_t,int64_t,int64_t);
#pragma GCC visibility pop
}
