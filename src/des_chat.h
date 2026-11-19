/*
 * des_chat.h - the application layer shared by tcpServer and tcpClient.
 *
 * Lab item 2.10:  create_message() -> encrypt_message() -> send_message()
 * Lab item 2.11:  receive_message() -> decrypt_message() -> display_message()
 *
 * Wire format of one message (all integers big-endian / network byte order):
 *
 *   +-------------+--------+-------------+--------------------------------+
 *   | length (4B) | mode   | IV (8B)     | ciphertext (length - 9 bytes,  |
 *   | = 9 + N     | 1=ECB  | 0 for ECB   |  N = multiple of 8)            |
 *   |             | 2=CBC  |             |                                |
 *   +-------------+--------+-------------+--------------------------------+
 *
 * Only the IV and the ciphertext travel over the network; the key is a
 * pre-shared secret configured on both machines (-k or $DES_KEY).
 */
#ifndef DES_CHAT_H
#define DES_CHAT_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "des.h"
#include "des_modes.h"

#define CHAT_DEFAULT_PORT 9000                /* same port as the starter code   */
#define CHAT_DEFAULT_KEY  "0f1571c947d9e859"  /* textbook key; -k / DES_KEY      */
#define CHAT_MAX_TEXT     4096                /* longest message in bytes        */
#define CHAT_MAX_CIPHER   (CHAT_MAX_TEXT + DES_BLOCK_SIZE)
#define CHAT_HEADER_SIZE  13                  /* 4 length + 1 mode + 8 IV        */
#define CHAT_EXIT         ":exit"             /* ends the conversation (starter) */

typedef struct {
    des_key_schedule ks;       /* K1..K16, generated once from the key      */
    uint64_t    key;
    des_mode    mode;
    int         color;         /* ANSI colours, only when writing to a tty  */
    int         trace;         /* -t: DES step table for the first block    */
    FILE       *input;         /* where messages are created from           */
    int         echo;          /* echo lines read from a file or a pipe     */
    const char *peer_label;    /* "client" or "Server", as in the starter   */
    char        peer[64];      /* "ip:port" of the other machine            */
    unsigned    sent;
    unsigned    received;
} chat_session;

typedef struct {
    uint8_t  mode;
    uint64_t iv;
    size_t   length;                       /* ciphertext bytes */
    uint8_t  ciphertext[CHAT_MAX_CIPHER];
} chat_packet;

/* key_hex / mode_name may be NULL (-> $DES_KEY or default key, CBC). */
int  chat_session_init(chat_session *s, const char *key_hex, const char *mode_name,
                       int trace, int no_color, const char *peer_label);
void chat_print_banner(const chat_session *s, const char *program, const char *role);
void chat_generate_keys(chat_session *s);

/* 2.10  create -> encrypt -> send */
int create_message(chat_session *s, char *text, size_t cap, size_t *len);
int encrypt_message(chat_session *s, const char *text, size_t len, chat_packet *pkt);
int send_message(chat_session *s, int sock, const chat_packet *pkt);

/* 2.11  receive -> decrypt -> display */
int  receive_message(chat_session *s, int sock, chat_packet *pkt);
int  decrypt_message(chat_session *s, const chat_packet *pkt, char *text, size_t cap,
                     size_t *len);
void display_message(chat_session *s, const char *text, size_t len);

/* One turn each.  1 = continue, 0 = conversation finished, -1 = error. */
int chat_send_turn(chat_session *s, int sock);
int chat_receive_turn(chat_session *s, int sock);

#endif /* DES_CHAT_H */
