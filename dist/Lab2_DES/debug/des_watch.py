# des_watch.py - GDB script: watch every DES step function with breakpoints.
#
#   gdb -q -batch -x debug/des_watch.py --args bin/des_trace -q
#
# A breakpoint on each step function reads the arguments (the INPUT) when the
# function is entered, and a FinishBreakpoint reads the return value (the
# OUTPUT) when it returns.  The program is never modified: these values are
# what the debugger observes in the running process.  Only the first call of
# each step is reported (round 1 / first round key), plus the last IP^-1.
import gdb

STEPS = [
    # function, lab item, DES step, argument names, bits of the output
    ("des_permuted_choice_1",           "2.4.1", "Permuted choice 1",       ["key:64"],                  56),
    ("des_left_circular_shift",         "2.4.2", "Left circular shift",     ["half:28", "amount:0"],     28),
    ("des_permuted_choice_2",           "2.4.3", "Permuted choice 2",       ["cd:56"],                   48),
    ("des_initial_permutation",         "2.1",   "Initial permutation",     ["block:64"],                64),
    ("des_expansion_permutation",       "2.3",   "Expansion/permutation",   ["right:32"],                48),
    ("des_xor_round_key",               "2.5",   "XOR with round key",      ["expanded:48", "subkey:48"], 48),
    ("des_sbox_lookup",                 "2.6",   "One S-box",               ["box:0", "six_bits:6"],      4),
    ("des_sbox_substitution",           "2.6",   "S-boxes",                 ["input48:48"],              32),
    ("des_permutation_p",               "2.7",   "Permutation P",           ["input:32"],                32),
    ("des_xor_left_half",               "2.8",   "XOR with left half",      ["left:32", "f_output:32"],  32),
    ("des_swap_halves",                 "2.9",   "Swap of the halves",      ["block:64"],                64),
    ("des_inverse_initial_permutation", "2.2",   "Inverse initial perm.",   ["block:64"],                64),
]

rows = []


def hex_value(value, bits):
    return format(int(value) & ((1 << bits) - 1), "0%dx" % ((bits + 3) // 4))


class ReturnWatch(gdb.FinishBreakpoint):
    def __init__(self, step, inputs):
        super().__init__(gdb.newest_frame(), internal=True)
        self.silent = True
        self.step, self.inputs = step, inputs

    def stop(self):
        function, item, name, _, bits = self.step
        rows.append((item, name, function, self.inputs, hex_value(self.return_value, bits)))
        return False

    def out_of_scope(self):
        pass


class StepWatch(gdb.Breakpoint):
    def __init__(self, step):
        super().__init__(step[0], internal=True)
        self.silent = True
        self.step = step
        self.hits = 0

    def stop(self):
        function, _, _, arg_names, _ = self.step
        self.hits += 1
        last_ip_inv = function == "des_inverse_initial_permutation"
        if self.hits == 1 or last_ip_inv:
            frame = gdb.selected_frame()
            parts = []
            for spec in arg_names:            # "name:bits", bits 0 = decimal
                name, bits = spec.split(":")
                value = int(frame.read_var(name))
                if bits == "0":
                    parts.append("%s=%d" % (name, value))
                elif bits == "6":
                    parts.append("%s=%s" % (name, format(value, "06b")))
                else:
                    parts.append("%s=%s" % (name, hex_value(value, int(bits))))
            inputs = ", ".join(parts)
            ReturnWatch(self.step, inputs)
        return False


gdb.execute("set pagination off")
gdb.execute("set confirm off")
for step in STEPS:
    StepWatch(step)
gdb.execute("run > /dev/null")

print("Values observed by GDB at the entry (input) and return (output) of each")
print("DES step function - first call of each step:\n")
print("%-6s %-22s %-32s %-48s %s" % ("item", "DES step", "function (method)", "input (arguments)", "output (return value)"))
print("-" * 134)
for item, name, function, inputs, output in rows:
    print("%-6s %-22s %-32s %-48s %s" % (item, name, function, inputs, output))
