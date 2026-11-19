/*
 * tcpClient.c - "Machine A" of the Lab 2 distributed DES application.
 *
 * Extended from the course starter tcpClient.c (socket -> connect, then a
 * turn-based conversation in which the client speaks first).  What was added
 * or fixed:
 *
 *  1. Every message is DES-encrypted before it is sent and decrypted after it
 *     is received (des_chat.c).
 *  2. The server is given on the command line (IP address or host name)
 *     instead of the hard-coded 127.0.0.1, so it can run on another computer.
 *     connect() is retried for a few seconds while the server is starting.
 *  3. Length-prefixed frames instead of C strings; fgets() instead of scanf.
 *  4. ":exit" is checked on the message just typed.  The starter compared the
 *     previously RECEIVED buffer (already cleared), so it never stopped.
 *
 * usage: tcpClient [-s server] [-p port] [-k key] [-m cbc|ecb] [-r retries] [-t] [-n]
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
            "usage: %s [-s server] [-p port] [-k key] [-m cbc|ecb] [-r retries] [-t] [-n]\n"
            "  -s server   IP address or host name of Machine B (default 127.0.0.1)\n"
            "  -p port     TCP port of the server            (default %d)\n"
            "  -k key      DES key, 16 hex digits  (default $DES_KEY or %s)\n"
            "  -m mode     cbc (default) or ecb\n"
            "  -r retries  connection attempts while the server starts (default 10)\n"
            "  -t          print the DES step table for the first block of each message\n"
            "  -n          no colours\n",
            prog, PORT, CHAT_DEFAULT_KEY);
}

int main(int argc, char *argv[])
{
    int clientSocket = -1, ret;
    struct sockaddr_in serverAddr;

    const char *server = "127.0.0.1", *key = NULL, *mode = NULL;
    int port = PORT, retries = 10, trace = 0, no_color = 0, opt;
    chat_session session;

    while ((opt = getopt(argc, argv, "s:p:k:m:r:tnh")) != -1) {
        switch (opt) {
        case 's': server = optarg; break;
        case 'p': port = atoi(optarg); break;
        case 'k': key = optarg; break;
        case 'm': mode = optarg; break;
        case 'r': retries = atoi(optarg); break;
        case 't': trace = 1; break;
        case 'n': no_color = 1; break;
        default: usage(argv[0]); return opt == 'h' ? 0 : 2;
        }
    }
    if (port <= 0 || port > 65535) {
        fprintf(stderr, "[-]Invalid port %d\n", port);
        return 2;
    }
    if (chat_session_init(&session, key, mode, trace, no_color, "Server") != 0)
        return 2;
    chat_print_banner(&session, "tcpClient",
                      "client (Machine A): connects to the server, sends first");
    chat_generate_keys(&session);

    memset(&serverAddr, '\0', sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons((uint16_t)port);
    if (net_resolve_ipv4(server, &serverAddr.sin_addr) != 0) {
        fprintf(stderr, "[-]Unknown server address: %s\n", server);
        exit(1);
    }
    net_endpoint(&serverAddr, session.peer, sizeof session.peer);

    for (int attempt = 0;; attempt++) {
        clientSocket = socket(AF_INET, SOCK_STREAM, 0);
        if (clientSocket < 0) {
            perror("[-]Error in connection");
            exit(1);
        }
        if (attempt == 0)
            printf("[+]Client Socket is created.\n");

        ret = connect(clientSocket, (struct sockaddr *)&serverAddr, sizeof(serverAddr));
        if (ret == 0)
            break;

        int err = errno;
        close(clientSocket);
        if (attempt >= retries) {
            fprintf(stderr, "[-]Error in connection to %s: %s\n", session.peer,
                    strerror(err));
            exit(1);
        }
        printf("[-]%s not reachable yet (%s), retry %d/%d in 1 s\n", session.peer,
               strerror(err), attempt + 1, retries);
        sleep(1);
    }

    struct sockaddr_in local;
    socklen_t local_len = sizeof local;
    char local_text[64] = "?";
    if (getsockname(clientSocket, (struct sockaddr *)&local, &local_len) == 0)
        net_endpoint(&local, local_text, sizeof local_text);
    printf("[+]Connected to Server %s from %s.\n", session.peer, local_text);

    /* Turn-based conversation, the client speaks first. */
    while (1) {
        if (chat_send_turn(&session, clientSocket) <= 0)     /* create, encrypt, send */
            break;
        if (chat_receive_turn(&session, clientSocket) <= 0)  /* receive, decrypt, display */
            break;
    }

    close(clientSocket);
    printf("[-]Disconnected from server.\n");
    return 0;
}
