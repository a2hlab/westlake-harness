/*
 * oh_inet_permit.c  —  西湖 (AOSP-on-OpenHarmony) INTERNET-permission boundary shim
 * Build: liboh_inet_permit.so   (LD_PRELOAD into appspawn-x; inherited by app children via fork)
 *
 * ── Problem ─────────────────────────────────────────────────────────────────
 * OH musl libc gates AF_INET/AF_INET6 socket creation behind a userspace
 * internet-permission flag, AND the resolver itself gates DNS:
 *
 *   third_party/musl/src/network/socket.c
 *     if ((domain==AF_INET || domain==AF_INET6) && is_allow_internet()==0) {
 *         errno = EPERM;  return -1;
 *     }
 *   third_party/musl/src/network/lookup_name.c  (name_from_dns_search)
 *     if (is_allow_internet() == 0) { errno = EPERM; return -1; }   // bails BEFORE any socket
 *
 *   is_allow_internet() dlopen()s libnetsys_client.z.so and reads
 *   IsAllowInternet() (the process-global g_allowInternet, default 1, cleared to
 *   0 only by DisallowInternet() which OH's real appspawn DoStartup() calls for
 *   apps WITHOUT ohos.permission.INTERNET).  It caches the result in a *libc-
 *   internal static* on first call, so it cannot be flipped from outside.
 *
 *   In the appspawn-x-forked Android child that flag resolves to 0, so every
 *   socket(AF_INET,...) returns EPERM, and the musl resolver short-circuits DNS
 *   entirely.  AOSP libcore turns the socket EPERM into a *fatal* SecurityException
 *   that kills the process before the first frame.
 *
 * ── Fix (HanBing iron-rule 3: adapt at the syscall/IPC boundary, never touch
 *    ART / class_linker / BCP Java) ────────────────────────────────────────────
 *   (1) socket():  for AF_INET/AF_INET6 bypass the OH internet-permission gate by
 *       issuing the raw socket(2) syscall directly (the kernel does NOT enforce
 *       internet permission — OH does it purely in the libc wrapper).  All other
 *       domains delegate to the real libc socket() so AF_UNIX/binder IPC keep
 *       musl's CLOEXEC/fdtrack handling untouched.  This alone lets the app's
 *       OkHttp open TCP sockets once it has an IP.
 *   (2) getaddrinfo():  the real resolver can never do DNS in the gated child
 *       (its own is_allow_internet() gate bails before creating a socket), so we
 *       run our OWN minimal DNS client here: build an A/AAAA query, send it over a
 *       UDP socket created via (1)'s raw-syscall path (gate-bypassed), parse the
 *       answer, and return real addresses laid out in musl's `struct aibuf` block
 *       so the app's own freeaddrinfo() frees them correctly.  If DNS still fails
 *       (no nameserver answered) we fall back to the old behaviour — clear errno
 *       and return EAI_NONAME so AOSP raises a recoverable UnknownHostException
 *       (the app degrades to "offline" instead of crashing).
 *
 * This neutralises the gate ONLY at the boundary; it changes no OH libc binary,
 * no ART, no BCP jar — pure LD_PRELOAD, hot-swappable, no boot rebake.
 */

#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/syscall.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <dlfcn.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>
#include <time.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/time.h>

/* ───────────────────────── optional HiLog diagnostics ─────────────────────── */
/* Resolve OH HiLogPrint lazily (libhilog is already loaded in the process). Logs
 * land in hilog under tag OH_InetPermit so the boundary behaviour is observable
 * without depending on any new lib at link time. */
typedef int (*hilog_fn)(int, int, unsigned int, const char *, const char *, ...);
static void ilog(const char *fmt, ...)
{
    static hilog_fn fn = (hilog_fn)-1;
    if (fn == (hilog_fn)-1) {
        fn = (hilog_fn)dlsym(RTLD_DEFAULT, "HiLogPrint");
    }
    if (!fn) return;
    char buf[512];
    va_list ap; __builtin_va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    __builtin_va_end(ap);
    /* LOG_CORE=3, LOG_INFO=4, domain 0xD000F00 */
    fn(3, 4, 0xD000F00u, "OH_InetPermit", "%{public}s", buf);
}

/* ───────────────────────── (1) socket(2) gate bypass ──────────────────────── */
int socket(int domain, int type, int protocol)
{
    if (domain == AF_INET || domain == AF_INET6) {
        /* Direct kernel syscall — skips musl's is_allow_internet() check.
         * musl's public syscall() sets errno and returns -1 on error. */
        long s = syscall(SYS_socket, (long)domain, (long)type, (long)protocol);
        return (int)s;
    }

    static int (*real_socket)(int, int, int) = 0;
    if (!real_socket) {
        real_socket = (int (*)(int, int, int))dlsym(RTLD_NEXT, "socket");
    }
    if (!real_socket) {
        errno = ENOSYS;
        return -1;
    }
    return real_socket(domain, type, protocol);
}

/* ───────────────────────── minimal DNS resolver ───────────────────────────── */
/* musl's struct aibuf — MUST match third_party/musl/src/network/lookup.h exactly
 * so the app's freeaddrinfo() (which computes the block base from the first node
 * and free()s it) works on the result we hand back. */
struct aibuf {
    struct addrinfo ai;
    union sa {
        struct sockaddr_in sin;
        struct sockaddr_in6 sin6;
    } sa;
    volatile int lock[1];
    short slot, ref;
};

#define DNS_T_A    1
#define DNS_T_AAAA 28
#define DNS_C_IN   1

static int dns_build_query(unsigned char *buf, const char *host,
                           int qtype, unsigned short id)
{
    buf[0] = (unsigned char)(id >> 8); buf[1] = (unsigned char)(id & 0xff);
    buf[2] = 0x01; buf[3] = 0x00;            /* RD set */
    buf[4] = 0;    buf[5] = 1;               /* QDCOUNT = 1 */
    buf[6] = buf[7] = buf[8] = buf[9] = buf[10] = buf[11] = 0;
    int p = 12;
    const char *s = host;
    while (*s) {
        const char *dot = strchr(s, '.');
        int len = dot ? (int)(dot - s) : (int)strlen(s);
        if (len <= 0 || len > 63) return -1;
        buf[p++] = (unsigned char)len;
        memcpy(buf + p, s, len); p += len;
        if (!dot) break;
        s = dot + 1;
    }
    buf[p++] = 0;
    buf[p++] = (unsigned char)(qtype >> 8); buf[p++] = (unsigned char)(qtype & 0xff);
    buf[p++] = 0; buf[p++] = DNS_C_IN;
    return p;
}

static int dns_skip_name(const unsigned char *msg, int len, int p)
{
    while (p >= 0 && p < len) {
        int c = msg[p];
        if ((c & 0xc0) == 0xc0) return p + 2;   /* compression pointer ends name */
        if (c == 0) return p + 1;
        p += c + 1;
    }
    return -1;
}

/* Parse answers; fill addrs[][16] + afam[]; return count. */
static int dns_parse(const unsigned char *msg, int len, int qtype,
                     unsigned char addrs[][16], int *afam, int maxn)
{
    if (len < 12) return 0;
    int ancount = (msg[6] << 8) | msg[7];
    int qd = (msg[4] << 8) | msg[5];
    int p = 12;
    for (int i = 0; i < qd; i++) {
        p = dns_skip_name(msg, len, p);
        if (p < 0) return 0;
        p += 4;                                  /* QTYPE + QCLASS */
    }
    int n = 0;
    for (int i = 0; i < ancount && p < len && n < maxn; i++) {
        p = dns_skip_name(msg, len, p);
        if (p < 0) break;
        if (p + 10 > len) break;
        int type  = (msg[p] << 8)   | msg[p + 1];
        int cls   = (msg[p + 2] << 8) | msg[p + 3];
        int rdlen = (msg[p + 8] << 8) | msg[p + 9];
        p += 10;
        if (p + rdlen > len) break;
        if (cls == DNS_C_IN && type == qtype) {
            if (type == DNS_T_A && rdlen == 4) {
                memcpy(addrs[n], msg + p, 4); afam[n] = AF_INET; n++;
            } else if (type == DNS_T_AAAA && rdlen == 16) {
                memcpy(addrs[n], msg + p, 16); afam[n] = AF_INET6; n++;
            }
        }
        p += rdlen;
    }
    return n;
}

/* Send a query to one nameserver (IPv4 dotted) and parse the reply. */
static int dns_query_ns(const char *ns_ip, const char *host, int qtype,
                        unsigned char addrs[][16], int *afam, int maxn)
{
    int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);  /* our socket() → raw bypass */
    if (fd < 0) return -1;

    struct timeval tv = { 3, 0 };
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);

    struct sockaddr_in sa;
    memset(&sa, 0, sizeof sa);
    sa.sin_family = AF_INET;
    sa.sin_port = htons(53);
    if (inet_pton(AF_INET, ns_ip, &sa.sin_addr) != 1) { close(fd); return -1; }

    unsigned char q[512];
    unsigned short id = (unsigned short)((getpid() << 8) ^ (unsigned)time(NULL));
    int qlen = dns_build_query(q, host, qtype, id);
    if (qlen < 0) { close(fd); return -1; }

    if (sendto(fd, q, qlen, 0, (struct sockaddr *)&sa, sizeof sa) != qlen) {
        close(fd); return -1;
    }

    unsigned char r[1500];
    ssize_t rl = recvfrom(fd, r, sizeof r, 0, NULL, NULL);
    close(fd);
    if (rl < 12) return -1;
    if (((r[0] << 8) | r[1]) != id) return -1;          /* txid mismatch */
    if ((r[3] & 0x0f) != 0) return 0;                   /* rcode != 0 (NXDOMAIN etc.) */
    return dns_parse(r, (int)rl, qtype, addrs, afam, maxn);
}

/* Build the nameserver candidate list: resolv.conf entries first, then known-good
 * public resolvers (8.8.8.8 is ICMP-proven reachable on this device; 114/223 are
 * reliable in CN networks).  De-duplicated. */
static int dns_nameservers(char ns[][64], int maxn)
{
    int n = 0;
    FILE *f = fopen("/etc/resolv.conf", "r");
    if (f) {
        char line[256];
        while (n < maxn && fgets(line, sizeof line, f)) {
            if (strncmp(line, "nameserver", 10) != 0) continue;
            char *p = line + 10;
            while (*p == ' ' || *p == '\t') p++;
            char *e = p;
            while (*e && *e != '\n' && *e != '\r' && *e != ' ' && *e != '\t') e++;
            *e = 0;
            if (*p) { strncpy(ns[n], p, 63); ns[n][63] = 0; n++; }
        }
        fclose(f);
    }
    static const char *fb[] = { "8.8.8.8", "114.114.114.114", "223.5.5.5", "1.1.1.1" };
    for (unsigned i = 0; i < sizeof(fb) / sizeof(fb[0]) && n < maxn; i++) {
        int dup = 0;
        for (int j = 0; j < n; j++) if (!strcmp(ns[j], fb[i])) { dup = 1; break; }
        if (!dup) { strncpy(ns[n], fb[i], 63); ns[n][63] = 0; n++; }
    }
    return n;
}

static unsigned short parse_port(const char *service)
{
    if (!service || !*service) return 0;
    if (isdigit((unsigned char)service[0])) return (unsigned short)atoi(service);
    if (!strcmp(service, "http"))  return 80;
    if (!strcmp(service, "https")) return 443;
    return 0;
}

/* Resolve `node` ourselves; on success build a musl-aibuf result. */
static int my_resolve(const char *node, const char *service,
                      const struct addrinfo *hints, struct addrinfo **res)
{
    int want = hints ? hints->ai_family : AF_UNSPEC;
    int qtype = (want == AF_INET6) ? DNS_T_AAAA : DNS_T_A;

    unsigned char addrs[16][16];
    int afam[16];
    char ns[10][64];
    int nns = dns_nameservers(ns, 10);

    int found = 0;
    for (int i = 0; i < nns && found == 0; i++) {
        int c = dns_query_ns(ns[i], node, qtype, addrs, afam, 16);
        if (c > 0) { found = c; ilog("resolved %s via %s -> %d addr(s)", node, ns[i], c); break; }
    }
    /* AF_UNSPEC asked for A above; if nothing, try AAAA as a courtesy. */
    if (found == 0 && want == AF_UNSPEC) {
        for (int i = 0; i < nns && found == 0; i++) {
            int c = dns_query_ns(ns[i], node, DNS_T_AAAA, addrs, afam, 16);
            if (c > 0) { found = c; break; }
        }
    }
    if (found <= 0) return EAI_NONAME;

    unsigned short port = parse_port(service);

    struct aibuf *out = calloc((size_t)found, sizeof *out);
    if (!out) return EAI_MEMORY;
    for (int i = 0; i < found; i++) {
        out[i].slot = (short)i;
        out[i].ai.ai_family   = afam[i];
        out[i].ai.ai_socktype = (hints && hints->ai_socktype) ? hints->ai_socktype : SOCK_STREAM;
        out[i].ai.ai_protocol = hints ? hints->ai_protocol : 0;
        out[i].ai.ai_flags = 0;
        out[i].ai.ai_canonname = NULL;
        if (afam[i] == AF_INET) {
            out[i].ai.ai_addrlen = sizeof(struct sockaddr_in);
            out[i].sa.sin.sin_family = AF_INET;
            out[i].sa.sin.sin_port = htons(port);
            memcpy(&out[i].sa.sin.sin_addr, addrs[i], 4);
        } else {
            out[i].ai.ai_addrlen = sizeof(struct sockaddr_in6);
            out[i].sa.sin6.sin6_family = AF_INET6;
            out[i].sa.sin6.sin6_port = htons(port);
            memcpy(&out[i].sa.sin6.sin6_addr, addrs[i], 16);
        }
        out[i].ai.ai_addr = (struct sockaddr *)&out[i].sa;
        out[i].ai.ai_next = (i + 1 < found) ? &out[i + 1].ai : NULL;
    }
    out[0].ref = (short)found;   /* freeaddrinfo: b->ref -= chain_len, free when 0 */
    *res = &out[0].ai;
    return 0;
}

/* ───────────────────────── (2) getaddrinfo override ───────────────────────── */
int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res)
{
    static int (*real_gai)(const char *, const char *,
                           const struct addrinfo *, struct addrinfo **) = 0;
    if (!real_gai) {
        real_gai = (int (*)(const char *, const char *,
                            const struct addrinfo *, struct addrinfo **))
                   dlsym(RTLD_NEXT, "getaddrinfo");
    }
    if (!real_gai) return EAI_SYSTEM;

    int rc = real_gai(node, service, hints, res);
    if (rc == 0) return 0;   /* numeric host / hosts-file / (ungated) DNS already worked */

    int gated = (rc == EAI_SYSTEM && (errno == EPERM || errno == EACCES));

    /* Real resolver failed.  For a hostname, do our own gate-bypassed DNS. */
    if (node && node[0]) {
        int myrc = my_resolve(node, service, hints, res);
        if (myrc == 0) return 0;
    }

    /* DNS unavailable: keep the app crash-free.  If the failure was the
     * internet-permission gate, clear errno + return a recoverable host-not-found
     * (UnknownHostException → "offline") instead of the fatal SecurityException. */
    if (gated) { errno = 0; return EAI_NONAME; }
    return rc;
}
