/* Minimal wpa_supplicant control client: send one command, print the reply.
 * usage: wpactl <ctrl-socket-path> <COMMAND...> */
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <ctrl-path> <command...>\n", argv[0]);
        return 2;
    }
    char cmd[256] = "";
    for (int i = 2; i < argc; i++) {
        if (i > 2) strncat(cmd, " ", sizeof(cmd) - strlen(cmd) - 1);
        strncat(cmd, argv[i], sizeof(cmd) - strlen(cmd) - 1);
    }
    int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) { perror("socket"); return 1; }
    struct sockaddr_un local = {.sun_family = AF_UNIX};
    snprintf(local.sun_path, sizeof(local.sun_path), "/data/local/tmp/wpactl-%d", getpid());
    unlink(local.sun_path);
    if (bind(fd, (struct sockaddr *)&local, sizeof(local)) < 0) { perror("bind"); return 1; }
    struct sockaddr_un dest = {.sun_family = AF_UNIX};
    snprintf(dest.sun_path, sizeof(dest.sun_path), "%s", argv[1]);
    if (connect(fd, (struct sockaddr *)&dest, sizeof(dest)) < 0) { perror("connect"); unlink(local.sun_path); return 1; }
    struct timeval tv = {.tv_sec = 5};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    if (send(fd, cmd, strlen(cmd), 0) < 0) { perror("send"); unlink(local.sun_path); return 1; }
    char buf[4096];
    ssize_t n = recv(fd, buf, sizeof(buf) - 1, 0);
    if (n < 0) { perror("recv"); unlink(local.sun_path); return 1; }
    buf[n] = '\0';
    fputs(buf, stdout);
    unlink(local.sun_path);
    close(fd);
    return 0;
}
