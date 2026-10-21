#pragma once
#include <cstdio>
#define APP_LOGD(...) ((void)0)
#define APP_LOGW(...) ((void)0)
#define APP_LOGE(fmt, ...) do { std::fprintf(stderr,"%s:%d:%s: %s\n",__FILE__,__LINE__,__func__,fmt); } while(0)
