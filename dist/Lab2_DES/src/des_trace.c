/*
 * des_trace.c - turns the des_trace() calls made in des.c into table rows:
 *               input -> method (C function) -> output -> DES step.
 */
#include "des_trace.h"

#include <string.h>

#include "des_util.h"

typedef unsigned long long ull;

/* What each step is called in the lab sheet and which function performs it. */
static const struct {
    const char *lab_item;
    const char *name;
    const char *function;
} STEP_INFO[DES_STEP_COUNT] = {
    [DES_STEP_PC1]         = {"2.4.1", "Permuted choice 1 (PC-1)",    "des_permuted_choice_1"},
    [DES_STEP_SHIFT_C]     = {"2.4.2", "Left circular shift of C",    "des_left_circular_shift"},
    [DES_STEP_SHIFT_D]     = {"2.4.2", "Left circular shift of D",    "des_left_circular_shift"},
    [DES_STEP_PC2]         = {"2.4.3", "Permuted choice 2 (PC-2)",    "des_permuted_choice_2"},
    [DES_STEP_IP]          = {"2.1",   "Initial permutation (IP)",    "des_initial_permutation"},
    [DES_STEP_EXPANSION]   = {"2.3",   "Expansion/permutation E",     "des_expansion_permutation"},
    [DES_STEP_XOR_KEY]     = {"2.5",   "XOR with round key",          "des_xor_round_key"},
    [DES_STEP_SBOX_LOOKUP] = {"2.6",   "One S-box (6 -> 4 bits)",     "des_sbox_lookup"},
    [DES_STEP_SBOX]        = {"2.6",   "S-boxes (48 -> 32 bits)",     "des_sbox_substitution"},
    [DES_STEP_P]           = {"2.7",   "Permutation P",               "des_permutation_p"},
    [DES_STEP_XOR_LEFT]    = {"2.8",   "XOR with left half",          "des_xor_left_half"},
    [DES_STEP_SWAP]        = {"2.9",   "Swap of the halves",          "des_swap_halves"},
    [DES_STEP_FINAL_SWAP]  = {"2.9",   "32-bit swap after round 16",  "des_swap_halves"},
    [DES_STEP_IP_INV]      = {"2.2",   "Inverse initial perm. IP^-1", "des_inverse_initial_permutation"},
};

static struct {
    des_trace_sink sink;
    void          *user;
    int            sbox_detail;
    int            max_blocks;
    int            blocks_done;
    int            seq;
    int            round;
    int            key_number;
    des_direction  dir;
} g_trace;

void des_trace_start(des_trace_sink sink, void *user, int with_sbox_detail,
                     int max_blocks)
{
    memset(&g_trace, 0, sizeof g_trace);
    g_trace.sink = sink;
    g_trace.user = user;
    g_trace.sbox_detail = with_sbox_detail;
    g_trace.max_blocks = max_blocks;
}

void des_trace_stop(void)
{
    g_trace.sink = NULL;
}

int des_trace_enabled(void)
{
    if (g_trace.sink == NULL)
        return 0;
    return g_trace.max_blocks == 0 || g_trace.blocks_done < g_trace.max_blocks;
}

void des_trace_round(int round, int key_number)
{
    g_trace.round = round;
    g_trace.key_number = key_number;
}

void des_trace_block_begin(des_direction dir)
{
    g_trace.dir = dir;
}

void des_trace_block_end(void)
{
    g_trace.blocks_done++;
}

static unsigned hi32(uint64_t v) { return (unsigned)(v >> 32); }
static unsigned lo32(uint64_t v) { return (unsigned)(v & 0xFFFFFFFFu); }
static unsigned hi28(uint64_t v) { return (unsigned)((v >> 28) & 0x0FFFFFFFu); }
static unsigned lo28(uint64_t v) { return (unsigned)(v & 0x0FFFFFFFu); }

/* Writes the "input" and "output" cells for one step. */
static void format_cells(des_step step, uint64_t a, uint64_t b, uint64_t out,
                         char *in, char *res, size_t cap)
{
    int r = g_trace.round;          /* current round i            */
    int p = g_trace.round - 1;      /* previous round i-1         */
    int k = g_trace.key_number;     /* subkey in use (Ki or K17-i) */
    const char *src = (g_trace.dir == DES_ENCRYPT) ? "P" : "C";
    const char *dst = (g_trace.dir == DES_ENCRYPT) ? "C" : "P";
    char bits[16];

    switch (step) {
    case DES_STEP_PC1:
        snprintf(in, cap, "K = %016llx", (ull)a);
        snprintf(res, cap, "C0 = %07x, D0 = %07x", hi28(out), lo28(out));
        break;
    case DES_STEP_SHIFT_C:
        snprintf(in, cap, "C%d = %07llx, shift %llu", p, (ull)a, (ull)b);
        snprintf(res, cap, "C%d = %07llx", r, (ull)out);
        break;
    case DES_STEP_SHIFT_D:
        snprintf(in, cap, "D%d = %07llx, shift %llu", p, (ull)a, (ull)b);
        snprintf(res, cap, "D%d = %07llx", r, (ull)out);
        break;
    case DES_STEP_PC2:
        snprintf(in, cap, "C%dD%d = %07x %07x", r, r, hi28(a), lo28(a));
        snprintf(res, cap, "K%d = %012llx", r, (ull)out);
        break;
    case DES_STEP_IP:
        snprintf(in, cap, "%s = %016llx", src, (ull)a);
        snprintf(res, cap, "L0 = %08x, R0 = %08x", hi32(out), lo32(out));
        break;
    case DES_STEP_EXPANSION:
        snprintf(in, cap, "R%d = %08llx", p, (ull)a);
        snprintf(res, cap, "E(R%d) = %012llx", p, (ull)out);
        break;
    case DES_STEP_XOR_KEY:
        snprintf(in, cap, "E = %012llx, K%d = %012llx", (ull)a, k, (ull)b);
        snprintf(res, cap, "E^K%d = %012llx", k, (ull)out);
        break;
    case DES_STEP_SBOX_LOOKUP: {
        unsigned six = (unsigned)b;
        unsigned row = ((six >> 4) & 0x2u) | (six & 0x1u);
        unsigned col = (six >> 1) & 0xFu;
        des_format_bits(bits, sizeof bits, six, 6, 0);
        snprintf(in, cap, "S%llu: %s (row %u, col %u)", (ull)a, bits, row, col);
        des_format_bits(bits, sizeof bits, out, 4, 0);
        snprintf(res, cap, "%s (%llu)", bits, (ull)out);
        break;
    }
    case DES_STEP_SBOX:
        snprintf(in, cap, "E^K%d = %012llx", k, (ull)a);
        snprintf(res, cap, "S = %08llx", (ull)out);
        break;
    case DES_STEP_P:
        snprintf(in, cap, "S = %08llx", (ull)a);
        snprintf(res, cap, "f(R%d,K%d) = %08llx", p, k, (ull)out);
        break;
    case DES_STEP_XOR_LEFT:
        snprintf(in, cap, "L%d = %08llx, f = %08llx", p, (ull)a, (ull)b);
        snprintf(res, cap, "L%d^f = %08llx", p, (ull)out);
        break;
    case DES_STEP_SWAP:
        snprintf(in, cap, "L%d^f | R%d = %08x %08x", p, p, hi32(a), lo32(a));
        snprintf(res, cap, "L%d | R%d = %08x %08x", r, r, hi32(out), lo32(out));
        break;
    case DES_STEP_FINAL_SWAP:
        snprintf(in, cap, "L16 | R16 = %08x %08x", hi32(a), lo32(a));
        snprintf(res, cap, "R16 | L16 = %08x %08x", hi32(out), lo32(out));
        break;
    case DES_STEP_IP_INV:
        snprintf(in, cap, "R16 | L16 = %08x %08x", hi32(a), lo32(a));
        snprintf(res, cap, "%s = %016llx", dst, (ull)out);
        break;
    default:
        snprintf(in, cap, "?");
        snprintf(res, cap, "?");
        break;
    }
}

void des_trace(des_step step, uint64_t a, uint64_t b, uint64_t out)
{
    if (!des_trace_enabled())
        return;
    if (step == DES_STEP_SBOX_LOOKUP && !g_trace.sbox_detail)
        return;

    des_trace_row row;
    memset(&row, 0, sizeof row);
    row.seq = ++g_trace.seq;
    row.round = g_trace.round;
    row.key_number = g_trace.key_number;
    row.step = step;
    row.lab_item = STEP_INFO[step].lab_item;
    row.step_name = STEP_INFO[step].name;
    row.function = STEP_INFO[step].function;
    row.detail = (step == DES_STEP_SBOX_LOOKUP);
    format_cells(step, a, b, out, row.input, row.output, sizeof row.input);

    g_trace.sink(&row, g_trace.user);
}

/* ------------------------------------------------------------------------ */
/*  Printer sink                                                             */
/* ------------------------------------------------------------------------ */

#define W_SEQ    4
#define W_ROUND  5
#define W_INPUT  36
#define W_METHOD 31
#define W_OUTPUT 30
#define W_STEP   36

static void table_rule(FILE *f)
{
    const int widths[] = {W_SEQ, W_ROUND, W_INPUT, W_METHOD, W_OUTPUT, W_STEP};
    fputc('+', f);
    for (size_t i = 0; i < sizeof widths / sizeof widths[0]; i++) {
        for (int j = 0; j < widths[i] + 2; j++)
            fputc('-', f);
        fputc('+', f);
    }
    fputc('\n', f);
}

/* CSV field with quotes doubled. */
static void csv_field(FILE *f, const char *text, int last)
{
    fputc('"', f);
    for (const char *c = text; *c; c++) {
        if (*c == '"')
            fputc('"', f);
        fputc(*c, f);
    }
    fputc('"', f);
    fputc(last ? '\n' : ',', f);
}

/* Rows are grouped as: key schedule (per round), IP, rounds 1..16, output. */
static int row_group(const des_trace_row *row)
{
    switch (row->step) {
    case DES_STEP_PC1:
        return 100;
    case DES_STEP_SHIFT_C:
    case DES_STEP_SHIFT_D:
    case DES_STEP_PC2:
        return 100 + row->round;
    case DES_STEP_IP:
        return 200;
    case DES_STEP_FINAL_SWAP:
    case DES_STEP_IP_INV:
        return 300;
    default:
        return 200 + row->round;
    }
}

void des_trace_printer_init(des_trace_printer *p, FILE *out, des_trace_format format)
{
    p->out = out;
    p->format = format;
    p->last_group = -1;
}

void des_trace_printer_header(des_trace_printer *p)
{
    FILE *f = p->out;
    switch (p->format) {
    case DES_TRACE_TABLE:
        table_rule(f);
        fprintf(f, "| %*s | %-*s | %-*s | %-*s | %-*s | %-*s |\n",
                W_SEQ, "#", W_ROUND, "Round", W_INPUT, "Input",
                W_METHOD, "Method (C function)", W_OUTPUT, "Output",
                W_STEP, "DES step (lab item)");
        table_rule(f);
        break;
    case DES_TRACE_CSV:
        fprintf(f, "seq,round,input,method,output,lab_item,des_step,detail\n");
        break;
    case DES_TRACE_MARKDOWN:
        fprintf(f, "| # | Round | Input | Method (C function) | Output | DES step (lab item) |\n");
        fprintf(f, "|--:|:-----:|-------|---------------------|--------|---------------------|\n");
        break;
    }
}

void des_trace_printer_row(const des_trace_row *row, void *printer)
{
    des_trace_printer *p = printer;
    FILE *f = p->out;
    char round[8], step[64];

    if (row->round > 0)
        snprintf(round, sizeof round, "%d", row->round);
    else
        snprintf(round, sizeof round, "-");
    snprintf(step, sizeof step, "%s %s", row->lab_item, row->step_name);

    switch (p->format) {
    case DES_TRACE_TABLE: {
        int group = row_group(row);
        if (p->last_group != -1 && group != p->last_group)
            table_rule(f);
        p->last_group = group;
        fprintf(f, "| %*d | %-*s | %-*s | %-*s | %-*s | %-*s |\n",
                W_SEQ, row->seq, W_ROUND, round, W_INPUT, row->input,
                W_METHOD, row->function, W_OUTPUT, row->output, W_STEP, step);
        break;
    }
    case DES_TRACE_CSV:
        fprintf(f, "%d,%d,", row->seq, row->round);
        csv_field(f, row->input, 0);
        csv_field(f, row->function, 0);
        csv_field(f, row->output, 0);
        csv_field(f, row->lab_item, 0);
        csv_field(f, row->step_name, 0);
        fprintf(f, "%d\n", row->detail);
        break;
    case DES_TRACE_MARKDOWN:
        fprintf(f, "| %d | %s | `%s` | `%s` | `%s` | %s |\n", row->seq, round,
                row->input, row->function, row->output, step);
        break;
    }
}

void des_trace_printer_footer(des_trace_printer *p)
{
    if (p->format == DES_TRACE_TABLE)
        table_rule(p->out);
}
