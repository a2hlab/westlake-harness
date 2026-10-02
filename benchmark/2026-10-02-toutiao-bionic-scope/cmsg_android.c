#include <stddef.h>
#include <stdint.h>

struct AndroidMsghdr {
    void* msg_name;
    uint32_t msg_namelen;
    void* msg_iov;
    size_t msg_iovlen;
    void* msg_control;
    size_t msg_controllen;
    int msg_flags;
};

struct AndroidCmsghdr {
    size_t cmsg_len;
    int cmsg_level;
    int cmsg_type;
};

_Static_assert(sizeof(void*) == 8, "Android LP64 only");
_Static_assert(sizeof(struct AndroidMsghdr) == 56, "Android msghdr size");
_Static_assert(offsetof(struct AndroidMsghdr, msg_control) == 32, "Android control offset");
_Static_assert(offsetof(struct AndroidMsghdr, msg_controllen) == 40, "Android length offset");
_Static_assert(sizeof(struct AndroidCmsghdr) == 16, "Android cmsghdr size");

struct AndroidCmsghdr* __cmsg_nxthdr(struct AndroidMsghdr* message, struct AndroidCmsghdr* current) {
    struct AndroidCmsghdr* next = (struct AndroidCmsghdr*)((char*)current +
        ((current->cmsg_len + sizeof(size_t) - 1) & ~(sizeof(size_t) - 1)));
    size_t length = (char*)(next + 1) - (char*)message->msg_control;
    if (length > message->msg_controllen) return NULL;
    return next;
}
