/*
 * tcpServer.c - "Machine B" of the Lab 2 distributed DES application.
 *
 * Extended from the course starter tcpServer.c.  The skeleton is unchanged
 * (socket -> bind -> listen -> accept, then a turn-based conversation in
 * which the client speaks first).  What was added or fixed:
 *
 *  1. Every message is DES-encrypted before it is sent and decrypted after it
 *     is received (des_chat.c: create/encrypt/send, receive/decrypt/display).
 *  2. bind() uses 0.0.0.0 (all interfaces) instead of 127.0.0.1; with
 *     127.0.0.1 a client on ANOTHER computer can never connect.  Address and
 *     port are command-line options (default port 9000, as in the starter).
 *  3. Messages travel as length-prefixed frames instead of C strings: the
 *     ciphertext can contain 0x00 bytes, and TCP may split or merge sends.
 *  4. Whole lines are read with fgets() instead of scanf("%s"), so messages
 *     can contain spaces and cannot overflow the buffer.
 *  5. addr_size is initialised before accept() and every recv() result is
 *     checked, so a closed connection is detected instead of looping.
 *  6. One client at a time (no fork()): the server's keyboard can only take
 *     part in one conversation at a time.
 *
 * usage: tcpServer [-p port] [-b address] [-k key] [-m cbc|ecb] [-1] [-t] [-n]
 */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include "des_chat.h"
#include "net.h"

#define PORT CHAT_DEFAULT_PORT

static void usage(const char *prog)
{
    fprintf(stderr,
            "usage: %s [-p port] [-b address] [-k key] [-m cbc|ecb] [-1] [-t] [-n]\n"
            "  -p port     TCP port to listen on            (default %d)\n"
            "  -b address  local address to bind            (default 0.0.0.0 = all)\n"
            "  -k key      DES key, 16 hex digits  (default $DES_KEY or %s)\n"
            "  -m mode     cbc (default) or ecb\n"
            "  -1          exit after the first client has disconnected\n"
            "  -t          print the DES step table for the first block of each message\n"
            "  -n          no colours\n",
            prog, PORT, CHAT_DEFAULT_KEY);
}

int main(int argc, char *argv[])
{
    int sockfd, ret;
    struct sockaddr_in serverAddr;
    int newSocket;
    struct sockaddr_in newAddr;
    socklen_t addr_size;

    int port = PORT, once = 0, trace = 0, no_color = 0, opt;
    const char *bind_address = "0.0.0.0", *key = NULL, *mode = NULL;
    chat_session session;

    while ((opt = getopt(argc, argv, "p:b:k:m:1tnh")) != -1) {
        switch (opt) {
        case 'p': port = atoi(optarg); break;
        case 'b': bind_address = optarg; break;
        case 'k': key = optarg; break;
        case 'm': mode = optarg; break;
        case '1': once = 1; break;
        case 't': trace = 1; break;
        case 'n': no_color = 1; break;
        default: usage(argv[0]); return opt == 'h' ? 0 : 2;
        }
    }
    if (port <= 0 || port > 65535) {
        fprintf(stderr, "[-]Invalid port %d\n", port);
        return 2;
    }
    if (chat_session_init(&session, key, mode, trace, no_color, "client") != 0)
        return 2;
    chat_print_banner(&session, "tcpServer",
                      "server (Machine B): waits for the client, receives first");
    chat_generate_keys(&session);

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("[-]Error in connection");
        exit(1);
    }
    printf("[+]Server Socket is created.\n");

    int reuse = 1;   /* allow an immediate restart on the same port */
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof reuse);

    memset(&serverAddr, '\0', sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, bind_address, &serverAddr.sin_addr) != 1) {
        fprintf(stderr, "[-]Invalid bind address: %s\n", bind_address);
        exit(1);
    }

    ret = bind(sockfd, (struct sockaddr *)&serverAddr, sizeof(serverAddr));
    if (ret < 0) {
        perror("[-]Error in binding");
        exit(1);
    }
    printf("[+]Bind to %s:%d is OK\n", bind_address, port);

    if (listen(sockfd, 10) == 0) {
        printf("[+]Listening....\n");
    } else {
        perror("[-]Error in listening");
        exit(1);
    }
    net_print_local_addresses(stdout, port);

    while (1) {
        addr_size = sizeof(newAddr);
        newSocket = accept(sockfd, (struct sockaddr *)&newAddr, &addr_size);
        if (newSocket < 0) {
            if (errno == EINTR)
                continue;
            perror("[-]Error in accept");
            exit(1);
        }
        net_endpoint(&newAddr, session.peer, sizeof session.peer);
        printf("Connection accepted from %s\n", session.peer);

        /* Turn-based conversation, the client speaks first. */
        while (1) {
            if (chat_receive_turn(&session, newSocket) <= 0)  /* receive, decrypt, display */
                break;
            if (chat_send_turn(&session, newSocket) <= 0)     /* create, encrypt, send */
                break;
        }

        printf("Disconnected from %s\n", session.peer);
        close(newSocket);
        if (once)
            break;
    }

    close(sockfd);
    return 0;
}
