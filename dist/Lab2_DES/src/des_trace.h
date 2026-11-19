/*
 * des_trace.h - records every DES step as one row of the table
 *
 *      #  | round | input | method (C function) | output | DES step (lab item)
 *
 * des.c calls des_trace(step, a, b, out) right after each step function.
 * Nothing is recorded unless a sink has been installed with des_trace_start(),
 * so normal encryption pays only for one "if" per step.
 */
#ifndef DES_TRACE_H
#define DES_TRACE_H

#include <stdint.h>
#include <stdio.h>

#include "des.h"

typedef enum {
    DES_STEP_PC1,          /* 2.4.1 permuted choice 1                  */
    DES_STEP_SHIFT_C,      /* 2.4.2 left circular shift of C           */
    DES_STEP_SHIFT_D,      /* 2.4.2 left circular shift of D           */
    DES_STEP_PC2,          /* 2.4.3 permuted choice 2                  */
    DES_STEP_IP,           /* 2.1   initial permutation                */
    DES_STEP_EXPANSION,    /* 2.3   expansion/permutation E            */
    DES_STEP_XOR_KEY,      /* 2.5   XOR with round key                 */
    DES_STEP_SBOX_LOOKUP,  /* 2.6   one S-box (detail rows, optional)  */
    DES_STEP_SBOX,         /* 2.6   all eight S-boxes                  */
    DES_STEP_P,            /* 2.7   permutation P                      */
    DES_STEP_XOR_LEFT,     /* 2.8   XOR with left half                 */
    DES_STEP_SWAP,         /* 2.9   swap of the halves                 */
    DES_STEP_FINAL_SWAP,   /* 2.9   32-bit swap after round 16         */
    DES_STEP_IP_INV,       /* 2.2   inverse initial permutation        */
    DES_STEP_COUNT
} des_step;

typedef struct {
    int         seq;         /* 1, 2, 3, ... in call order                 */
    int         round;       /* 1..16 inside a round, 0 outside            */
    int         key_number;  /* which Ki is in use (differs when decrypting) */
    des_step    step;
    const char *lab_item;    /* e.g. "2.4.1"                               */
    const char *step_name;   /* e.g. "Permuted choice 1 (PC-1)"            */
    const char *function;    /* e.g. "des_permuted_choice_1"               */
    int         detail;      /* 1 for the optional per-S-box rows          */
    char        input[96];
    char        output[96];
} des_trace_row;

typedef void (*des_trace_sink)(const des_trace_row *row, void *user);

/* Install a sink (NULL = tracing off).
 *   with_sbox_detail : also emit the 8 individual S-box look-ups per round
 *   max_blocks       : stop after this many blocks (0 = no limit)          */
void des_trace_start(des_trace_sink sink, void *user, int with_sbox_detail,
                     int max_blocks);
void des_trace_stop(void);
int  des_trace_enabled(void);

/* Hooks used by des.c */
void des_trace(des_step step, uint64_t a, uint64_t b, uint64_t out);
void des_trace_round(int round, int key_number);
void des_trace_block_begin(des_direction dir);
void des_trace_block_end(void);

/* A ready-made sink that prints the rows as a text table, CSV or Markdown. */
typedef enum {
    DES_TRACE_TABLE,
    DES_TRACE_CSV,
    DES_TRACE_MARKDOWN
} des_trace_format;

typedef struct {
    FILE            *out;
    des_trace_format format;
    int              last_group;   /* used to draw separators between rounds */
} des_trace_printer;

void des_trace_printer_init(des_trace_printer *p, FILE *out, des_trace_format format);
void des_trace_printer_header(des_trace_printer *p);
void des_trace_printer_row(const des_trace_row *row, void *printer);  /* a sink */
void des_trace_printer_footer(des_trace_printer *p);

#endif /* DES_TRACE_H */
