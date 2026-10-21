#pragma once
#include <cstring>
#include <cerrno>
#define EOK 0
inline int memset_s(void*d,size_t n,int c,size_t k){ if(!d||k>n)return EINVAL;std::memset(d,c,k);return 0;}
inline int memcpy_s(void*d,size_t n,const void*s,size_t k){if(!d||!s||k>n)return EINVAL;std::memcpy(d,s,k);return 0;}
