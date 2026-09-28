#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

enum OracleExit {
    ORACLE_CONNECTED = 0,
    ORACLE_ENDPOINT_ABSENT = 20,
    ORACLE_SOCKET_FAILED = 21,
    ORACLE_CONNECT_FAILED = 22,
};

static const char kEndpoint[] = "/dev/unix/socket/AppSpawnX";

int main(void)
{
    struct sockaddr_un peer;
    struct stat endpoint_stat;
    int stat_result;
    int stat_error;
    int socket_fd;
    int connect_result;
    int connect_error;
    int result;
    const char *verdict;
    const char *endpoint_kind;
    socklen_t peer_length;

    _Static_assert(sizeof(kEndpoint) <= sizeof(peer.sun_path),
                   "AppSpawnX pathname exceeds sockaddr_un capacity");

    errno = 0;
    stat_result = lstat(kEndpoint, &endpoint_stat);
    stat_error = stat_result == 0 ? 0 : errno;
    if (stat_result == 0) {
        endpoint_kind = S_ISSOCK(endpoint_stat.st_mode) ? "socket" : "non_socket";
    } else if (stat_error == ENOENT) {
        endpoint_kind = "absent";
    } else {
        endpoint_kind = "stat_error";
    }

    socket_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (socket_fd < 0) {
        connect_result = -1;
        connect_error = errno;
        result = ORACLE_SOCKET_FAILED;
        verdict = "SOCKET_FAILED";
    } else {
        memset(&peer, 0, sizeof(peer));
        peer.sun_family = AF_UNIX;
        memcpy(peer.sun_path, kEndpoint, sizeof(kEndpoint));
        peer_length = (socklen_t)(offsetof(struct sockaddr_un, sun_path) +
                                  sizeof(kEndpoint));

        errno = 0;
        connect_result = connect(socket_fd, (const struct sockaddr *)&peer,
                                 peer_length);
        connect_error = connect_result == 0 ? 0 : errno;
        (void)close(socket_fd);

        if (connect_result == 0) {
            result = ORACLE_CONNECTED;
            verdict = "CONNECTED";
        } else if (connect_error == ENOENT) {
            result = ORACLE_ENDPOINT_ABSENT;
            verdict = "ENOENT";
        } else {
            result = ORACLE_CONNECT_FAILED;
            verdict = "CONNECT_FAILED";
        }
    }

    printf("M02_APPSPAWNX_CONNECT_ORACLE endpoint=%s endpoint_kind=%s "
           "stat_rc=%d stat_errno=%d connect_rc=%d connect_errno=%d "
           "verdict=%s exit=%d\n",
           kEndpoint, endpoint_kind, stat_result, stat_error, connect_result,
           connect_error, verdict, result);
    return result;
}

