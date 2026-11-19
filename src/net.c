/*
 * net.c - small TCP helpers used by tcpServer.c and tcpClient.c.
 */
#include "net.h"

#include <arpa/inet.h>
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netdb.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

int net_send_all(int sock, const void *buf, size_t len)
{
    const unsigned char *p = buf;
    while (len > 0) {
        /* MSG_NOSIGNAL: report a closed peer as an error instead of SIGPIPE */
        ssize_t n = send(sock, p, len, MSG_NOSIGNAL);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        p += n;
        len -= (size_t)n;
    }
    return 0;
}

int net_recv_all(int sock, void *buf, size_t len)
{
    unsigned char *p = buf;
    size_t got = 0;
    while (got < len) {
        ssize_t n = recv(sock, p + got, len - got, 0);
        if (n == 0)
            return got == 0 ? 0 : -1;   /* closed (in the middle = error) */
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        got += (size_t)n;
    }
    return 1;
}

void net_print_local_addresses(FILE *f, int port)
{
    struct ifaddrs *list = NULL;
    if (getifaddrs(&list) != 0)
        return;
    for (struct ifaddrs *it = list; it != NULL; it = it->ifa_next) {
        if (it->ifa_addr == NULL || it->ifa_addr->sa_family != AF_INET)
            continue;
        if (it->ifa_flags & IFF_LOOPBACK)
            continue;
        char ip[INET_ADDRSTRLEN];
        const struct sockaddr_in *sin = (const struct sockaddr_in *)(void *)it->ifa_addr;
        inet_ntop(AF_INET, &sin->sin_addr, ip, sizeof ip);
        fprintf(f, "[+]Clients can connect to %s:%d (interface %s)\n", ip, port,
                it->ifa_name);
    }
    freeifaddrs(list);
}

char *net_endpoint(const struct sockaddr_in *addr, char *buf, size_t cap)
{
    char ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &addr->sin_addr, ip, sizeof ip);
    snprintf(buf, cap, "%s:%u", ip, (unsigned)ntohs(addr->sin_port));
    return buf;
}

int net_resolve_ipv4(const char *host, struct in_addr *out)
{
    if (inet_pton(AF_INET, host, out) == 1)
        return 0;

    struct addrinfo hints, *result = NULL;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(host, NULL, &hints, &result) != 0 || result == NULL)
        return -1;
    *out = ((const struct sockaddr_in *)(void *)result->ai_addr)->sin_addr;
    freeaddrinfo(result);
    return 0;
}
