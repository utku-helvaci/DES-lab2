/*
 * net.h - small TCP helpers used by tcpServer.c and tcpClient.c.
 */
#ifndef NET_H
#define NET_H

#include <netinet/in.h>
#include <stddef.h>
#include <stdio.h>

/* send() until every byte is written.  0 = ok, -1 = error. */
int net_send_all(int sock, const void *buf, size_t len);

/* recv() until exactly len bytes arrived (TCP may deliver a message in
 * pieces).  1 = ok, 0 = peer closed before the first byte, -1 = error. */
int net_recv_all(int sock, void *buf, size_t len);

/* Print the IPv4 address of every non-loopback interface ("eth0 1.2.3.4"). */
void net_print_local_addresses(FILE *f, int port);

/* "a.b.c.d:port" */
char *net_endpoint(const struct sockaddr_in *addr, char *buf, size_t cap);

/* Dotted-quad address or host name (e.g. "machine-b") -> IPv4 address. */
int net_resolve_ipv4(const char *host, struct in_addr *out);

#endif /* NET_H */
