/*
 * des_chat.c - create/encrypt/send and receive/decrypt/display, with every
 * stage printed so that it can be seen (and screenshotted) on both machines.
 */
#include "des_chat.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "des_trace.h"
#include "des_util.h"
#include "net.h"

/* ANSI colours for the stage tags (disabled when stdout is not a terminal) */
#define C_RESET   "\033[0m"
#define C_DIM     "\033[2m"
#define C_BOLD    "\033[1m"
#define C_CREATE  "\033[1;36m"
#define C_ENCRYPT "\033[1;33m"
#define C_SEND    "\033[1;34m"
#define C_RECEIVE "\033[1;35m"
#define C_DECRYPT "\033[1;33m"
#define C_DISPLAY "\033[1;32m"
#define C_ERROR   "\033[1;31m"

#define INDENT      "          "                     /* under "[ENCRYPT] " */
#define HEX_INDENT  INDENT "                   "      /* under the hex dump */

static const char *col(const chat_session *s, const char *code)
{
    return s->color ? code : "";
}

static void stage(const chat_session *s, const char *code, const char *tag,
                  const char *fmt, ...)
{
    va_list ap;
    printf("%s[%-7s]%s ", col(s, code), tag, col(s, C_RESET));
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
}

/* "          ciphertext   24 B  0123456789abcdef 0123..." */
static void hex_line(const char *label, const uint8_t *data, size_t len)
{
    printf("%s%-10s %4zu B  ", INDENT, label, len);
    if (len == 0)
        printf("(empty)\n");
    else
        des_print_hex_blocks(stdout, data, len, HEX_INDENT, 4);
}

/* Printable copy of a message: control characters become \xNN, UTF-8 stays. */
static const char *printable(const char *text, size_t len)
{
    static char out[4 * CHAT_MAX_CIPHER + 1];
    size_t pos = 0;
    for (size_t i = 0; i < len && pos + 5 < sizeof out; i++) {
        unsigned char c = (unsigned char)text[i];
        if (c < 0x20 || c == 0x7f)
            pos += (size_t)snprintf(out + pos, sizeof out - pos, "\\x%02x", c);
        else
            out[pos++] = (char)c;
    }
    out[pos] = '\0';
    return out;
}

static void rule(const chat_session *s, const char *title)
{
    printf("%s---- %s ", col(s, C_DIM), title);
    for (size_t i = strlen(title); i < 70; i++)
        putchar('-');
    printf("%s\n", col(s, C_RESET));
}

/* ------------------------------------------------------------------------ */

int chat_session_init(chat_session *s, const char *key_hex, const char *mode_name,
                      int trace, int no_color, const char *peer_label)
{
    memset(s, 0, sizeof *s);

    if (key_hex == NULL || *key_hex == '\0')
        key_hex = getenv("DES_KEY");
    if (key_hex == NULL || *key_hex == '\0')
        key_hex = CHAT_DEFAULT_KEY;
    if (des_parse_hex64(key_hex, &s->key) != 0) {
        fprintf(stderr, "[-]Invalid DES key (16 hex digits expected): %s\n", key_hex);
        return -1;
    }

    s->mode = DES_MODE_CBC;
    if (mode_name != NULL && des_mode_parse(mode_name, &s->mode) != 0) {
        fprintf(stderr, "[-]Unknown mode '%s' (use cbc or ecb)\n", mode_name);
        return -1;
    }

    setvbuf(stdout, NULL, _IOLBF, 0);   /* line by line, also into pipes/logs */
    s->trace = trace;
    s->color = !no_color && isatty(STDOUT_FILENO) && getenv("NO_COLOR") == NULL;
    s->input = stdin;
    s->echo = !isatty(STDIN_FILENO);
    s->peer_label = peer_label;
    snprintf(s->peer, sizeof s->peer, "?");
    return 0;
}

void chat_print_banner(const chat_session *s, const char *program, const char *role)
{
    char host[256] = "?";
    gethostname(host, sizeof host - 1);

    printf("%s", col(s, C_BOLD));
    printf("==============================================================================\n");
    printf(" CMPE455/CMSE456 Lab 2 - DES on two computers                 %s\n", program);
    printf("==============================================================================\n");
    printf("%s", col(s, C_RESET));
    printf(" host name : %s\n", host);
    printf(" role      : %s\n", role);
    printf(" DES key   : %016llx  (pre-shared; PC-1 keeps 56 of the 64 bits)\n",
           (unsigned long long)s->key);
    if (s->mode == DES_MODE_CBC)
        printf(" mode      : DES-CBC, PKCS#7 padding, new random IV for every message\n");
    else
        printf(" mode      : DES-ECB, PKCS#7 padding (no IV)\n");
    printf(" exit word : %s  (or end of input / Ctrl-D)\n", CHAT_EXIT);
    printf("------------------------------------------------------------------------------\n");
}

void chat_generate_keys(chat_session *s)
{
    des_trace_printer printer;

    if (s->trace) {
        printf("DES key schedule (lab item 2.4): PC-1, left circular shifts, PC-2\n");
        des_trace_printer_init(&printer, stdout, DES_TRACE_TABLE);
        des_trace_printer_header(&printer);
        des_trace_start(des_trace_printer_row, &printer, 0, 0);
    }
    des_generate_round_keys(s->key, &s->ks);                  /* 2.4 */
    if (s->trace) {
        des_trace_stop();
        des_trace_printer_footer(&printer);
    }
    printf("[+]Round keys generated: K1 = %012llx ... K16 = %012llx\n",
           (unsigned long long)s->ks.subkey[0],
           (unsigned long long)s->ks.subkey[DES_ROUNDS - 1]);
}

static void trace_first_block(des_trace_printer *printer, const char *what)
{
    printf("%sDES steps for %s:\n", INDENT, what);
    des_trace_printer_init(printer, stdout, DES_TRACE_TABLE);
    des_trace_printer_header(printer);
    des_trace_start(des_trace_printer_row, printer, 0, 1);   /* one block */
}

static void trace_done(des_trace_printer *printer)
{
    des_trace_stop();
    des_trace_printer_footer(printer);
}

/* ======================= 2.10  create -> encrypt -> send ================== */

int create_message(chat_session *s, char *text, size_t cap, size_t *len)
{
    printf("Enter your message: ");
    fflush(stdout);

    if (fgets(text, (int)cap, s->input) == NULL) {
        /* End of input (Ctrl-D, or the end of a script file): say goodbye. */
        snprintf(text, cap, "%s", CHAT_EXIT);
        printf("%s   (end of input)\n", CHAT_EXIT);
    } else {
        size_t n = strcspn(text, "\r\n");
        if (text[n] == '\0' && n == cap - 1) {
            int c;   /* line longer than the buffer: drop the rest of it */
            while ((c = fgetc(s->input)) != '\n' && c != EOF) {
            }
            fprintf(stderr, "[!]Message truncated to %zu bytes\n", n);
        }
        text[n] = '\0';
        if (s->echo)
            printf("%s\n", text);
    }

    *len = strlen(text);
    s->sent++;
    stage(s, C_CREATE, "CREATE", "message #%u, %zu bytes: \"%s\"", s->sent, *len,
          printable(text, *len));
    return 0;
}

int encrypt_message(chat_session *s, const char *text, size_t len, chat_packet *pkt)
{
    pkt->mode = (uint8_t)s->mode;
    pkt->iv = 0;
    if (s->mode == DES_MODE_CBC) {
        uint8_t iv_bytes[DES_BLOCK_SIZE];
        if (des_random_bytes(iv_bytes, sizeof iv_bytes) != 0) {
            stage(s, C_ERROR, "ERROR", "cannot read /dev/urandom for the IV");
            return -1;
        }
        pkt->iv = des_load_block(iv_bytes);
        stage(s, C_ENCRYPT, "ENCRYPT", "DES-CBC   key = %016llx   IV = %016llx",
              (unsigned long long)s->key, (unsigned long long)pkt->iv);
    } else {
        stage(s, C_ENCRYPT, "ENCRYPT", "DES-ECB   key = %016llx",
              (unsigned long long)s->key);
    }

    /* Show the padded plaintext exactly as the cipher will see it. */
    uint8_t padded[CHAT_MAX_CIPHER];
    size_t padded_len = des_padded_size(len);
    memcpy(padded, text, len);
    memset(padded + len, (int)(padded_len - len), padded_len - len);
    hex_line("plaintext", (const uint8_t *)text, len);
    hex_line("+ PKCS#7", padded, padded_len);

    des_trace_printer printer;
    if (s->trace)
        trace_first_block(&printer, s->mode == DES_MODE_CBC
                                        ? "block 1 (input = P1 XOR IV)" : "block 1");
    pkt->length = des_encrypt_message(s->mode, &s->ks, pkt->iv,
                                      (const uint8_t *)text, len, pkt->ciphertext);
    if (s->trace)
        trace_done(&printer);

    hex_line("ciphertext", pkt->ciphertext, pkt->length);
    return 0;
}

int send_message(chat_session *s, int sock, const chat_packet *pkt)
{
    uint8_t frame[CHAT_HEADER_SIZE + CHAT_MAX_CIPHER];
    uint32_t length = (uint32_t)(1 + DES_BLOCK_SIZE + pkt->length);

    frame[0] = (uint8_t)(length >> 24);         /* length, network byte order */
    frame[1] = (uint8_t)(length >> 16);
    frame[2] = (uint8_t)(length >> 8);
    frame[3] = (uint8_t)length;
    frame[4] = pkt->mode;
    des_store_block(pkt->iv, frame + 5);
    memcpy(frame + CHAT_HEADER_SIZE, pkt->ciphertext, pkt->length);

    size_t total = CHAT_HEADER_SIZE + pkt->length;
    if (net_send_all(sock, frame, total) != 0) {
        stage(s, C_ERROR, "ERROR", "send() to %s failed", s->peer);
        return -1;
    }
    stage(s, C_SEND, "SEND", "%zu bytes -> %s  (13-byte header + %zu-byte ciphertext)",
          total, s->peer, pkt->length);
    return 0;
}

/* ===================== 2.11  receive -> decrypt -> display ================ */

int receive_message(chat_session *s, int sock, chat_packet *pkt)
{
    uint8_t header[CHAT_HEADER_SIZE];
    int r = net_recv_all(sock, header, sizeof header);
    if (r == 0) {
        printf("[-]The %s closed the connection.\n", s->peer_label);
        return 0;
    }
    if (r < 0) {
        stage(s, C_ERROR, "ERROR", "recv() from %s failed", s->peer);
        return -1;
    }

    uint32_t length = ((uint32_t)header[0] << 24) | ((uint32_t)header[1] << 16) |
                      ((uint32_t)header[2] << 8) | header[3];
    if (length < 1 + DES_BLOCK_SIZE + DES_BLOCK_SIZE ||
        length - 1 - DES_BLOCK_SIZE > CHAT_MAX_CIPHER ||
        (length - 1 - DES_BLOCK_SIZE) % DES_BLOCK_SIZE != 0) {
        stage(s, C_ERROR, "ERROR", "invalid frame length %u", length);
        return -1;
    }
    pkt->mode = header[4];
    pkt->iv = des_load_block(header + 5);
    pkt->length = length - 1 - DES_BLOCK_SIZE;

    if (net_recv_all(sock, pkt->ciphertext, pkt->length) != 1) {
        stage(s, C_ERROR, "ERROR", "connection lost in the middle of a message");
        return -1;
    }
    s->received++;
    stage(s, C_RECEIVE, "RECEIVE", "%zu bytes <- %s  (13-byte header + %zu-byte ciphertext)",
          CHAT_HEADER_SIZE + pkt->length, s->peer, pkt->length);
    hex_line("ciphertext", pkt->ciphertext, pkt->length);
    return 1;
}

int decrypt_message(chat_session *s, const chat_packet *pkt, char *text, size_t cap,
                    size_t *len)
{
    des_mode mode = (des_mode)pkt->mode;
    if (mode == DES_MODE_CBC) {
        stage(s, C_DECRYPT, "DECRYPT", "DES-CBC   key = %016llx   IV = %016llx",
              (unsigned long long)s->key, (unsigned long long)pkt->iv);
    } else if (mode == DES_MODE_ECB) {
        stage(s, C_DECRYPT, "DECRYPT", "DES-ECB   key = %016llx",
              (unsigned long long)s->key);
    } else {
        stage(s, C_ERROR, "ERROR", "unknown mode %u in the received frame", pkt->mode);
        return -1;
    }

    uint8_t plain[CHAT_MAX_CIPHER];
    size_t plain_len = 0;
    des_trace_printer printer;
    if (s->trace)
        trace_first_block(&printer, mode == DES_MODE_CBC
                                        ? "block 1 (output XOR IV = P1)" : "block 1");
    int rc = des_decrypt_message(mode, &s->ks, pkt->iv, pkt->ciphertext, pkt->length,
                                 plain, &plain_len);
    if (s->trace)
        trace_done(&printer);

    if (rc == DES_ERR_LENGTH || rc == DES_ERR_MODE) {
        stage(s, C_ERROR, "ERROR", "malformed ciphertext");
        return -1;
    }
    hex_line("decrypted", plain, pkt->length);
    if (rc == DES_ERR_PADDING) {
        stage(s, C_ERROR, "ERROR",
              "padding check failed: the two machines are not using the same key");
        return -1;
    }
    printf("%s%-10s %4zu B  removed -> %zu-byte message\n", INDENT, "padding",
           pkt->length - plain_len, plain_len);

    if (plain_len >= cap)
        plain_len = cap - 1;
    memcpy(text, plain, plain_len);
    text[plain_len] = '\0';
    *len = plain_len;
    return 0;
}

void display_message(chat_session *s, const char *text, size_t len)
{
    stage(s, C_DISPLAY, "DISPLAY", "Message from the %s: %s\"%s\"%s", s->peer_label,
          col(s, C_BOLD), printable(text, len), col(s, C_RESET));
}

/* ======================= one turn of the conversation ===================== */

int chat_send_turn(chat_session *s, int sock)
{
    char text[CHAT_MAX_TEXT];
    size_t len = 0;
    chat_packet pkt;

    rule(s, "your turn: create -> encrypt -> send");
    if (create_message(s, text, sizeof text, &len) != 0)
        return -1;
    if (encrypt_message(s, text, len, &pkt) != 0)
        return -1;
    if (send_message(s, sock, &pkt) != 0)
        return -1;
    return strcmp(text, CHAT_EXIT) == 0 ? 0 : 1;
}

int chat_receive_turn(chat_session *s, int sock)
{
    char text[CHAT_MAX_CIPHER + 1];
    size_t len = 0;
    chat_packet pkt;

    rule(s, "peer's turn: receive -> decrypt -> display");
    printf("Waiting for a message from the %s ...\n", s->peer_label);
    int r = receive_message(s, sock, &pkt);
    if (r <= 0)
        return r;
    if (decrypt_message(s, &pkt, text, sizeof text, &len) != 0)
        return -1;
    display_message(s, text, len);
    if (strcmp(text, CHAT_EXIT) == 0) {
        printf("[-]The %s ended the conversation.\n", s->peer_label);
        return 0;
    }
    return 1;
}
