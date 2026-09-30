#ifndef WESTLAKE_MUSL_SOCKET_FIX_H
#define WESTLAKE_MUSL_SOCKET_FIX_H

#include <sys/socket.h>

#define _UAPI_LINUX_SOCKET_H
#ifndef _K_SS_MAXSIZE
#define _K_SS_MAXSIZE 128
#endif
typedef unsigned short __kernel_sa_family_t;
#ifndef SOCK_CLOEXEC
#define SOCK_CLOEXEC 02000000
#endif
#ifndef SOCK_NONBLOCK
#define SOCK_NONBLOCK 04000
#endif

#endif
