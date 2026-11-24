# Study guide: DES on Two Computers

Questions the evaluator might ask, from easy to difficult. **★ = very likely.** If you are
short of time, read only the ★ questions and the two sections below.

Everything matches `lab2.c`, `Dockerfile` and `docker-compose.yml` in this folder. The
answers to the "what happens if ..." questions were tried out with the program.

| Level | Questions | Topic |
|---|---|---|
| 1 | 1 - 15 | Common knowledge: Docker, networks, encryption |
| 2 | 16 - 26 | DES in general |
| 3 | 27 - 37 | The DES steps |
| 4 | 38 - 48 | Our Docker and network setup |
| 5 | 49 - 64 | Our code |
| 6 | 65 - 80 | Hard: what happens if ..., security, weak points |
| 7 | 81 - 91 | "Do it in front of me": by hand and live changes |

## The project in 30 seconds ★

> We implemented DES in C, with one function for every step. Two Docker containers play
> the two computers. The same program runs on both: one is the server, the other is the
> client. They take turns. One side types a message, the program encrypts it with DES and
> sends it over TCP; the other side receives it, decrypts it and displays it. We compared
> the steps with the example in the handout, and a packet capture shows that only
> ciphertext is on the network.

## Numbers to know by heart ★

| What | Value |
|---|---|
| Block | 64 bits = 8 bytes = 16 hex digits |
| Key | 64 bits, only 56 are used (8 are parity bits) |
| Rounds and round keys | 16 rounds, 16 round keys of 48 bits |
| Halves | L and R: 32 bits each; C and D (key): 28 bits each |
| S-boxes | 8 boxes, 6 bits in, 4 bits out, 4 rows x 16 columns |
| Example key | `0f1571c947d9e859` |
| Example plaintext | `02468aceeca86420` |
| Example ciphertext | `da02ce3a89ecac3b` |
| After IP | L0 = `5a005a00`, R0 = `3cf03c0f` |
| First round key | K1 = `7833c320da70` |
| After round 1 | L1 = `3cf03c0f`, R1 = `bad22845` |
| Machine A | 172.28.20.10, client, sends first |
| Machine B | 172.28.20.20, server, port 9000 |

---

# Level 1: common knowledge

### 1. ★ What does this Docker do?

Docker runs programs in containers. A container is an isolated environment with its own
file system, processes and network, but it uses the kernel of the host computer. In our
lab Docker plays the two computers: it starts two containers, `machine-a` and `machine-b`,
and connects them with a virtual network. So two processes on two "machines" can talk over
TCP.

### 2. What is the difference between an image and a container?

An image is the read-only template: the file system with the program in it. A container is
a running copy of an image. Both of our containers are built from the same Dockerfile.

### 3. ★ What is the difference between a container and a virtual machine?

A virtual machine has its own operating system kernel and virtual hardware, so it is big
and starts slowly. A container shares the kernel of the host, so it is small and starts in
about a second. A virtual machine is isolated more strongly.

### 4. What are the Dockerfile and docker-compose.yml?

The Dockerfile is the recipe for the image: which system, which packages, which program.
`docker-compose.yml` describes the whole setup: two containers, their host names, their IP
addresses and the network. One command then starts everything.

### 5. What are a client and a server?

The server waits for connections; the client connects to it. In our lab Machine B is the
server and Machine A is the client. After connecting, both can send and receive.

### 6. What are an IP address and a port?

The IP address identifies the machine, the port identifies the program on that machine.
Our server is at 172.28.20.20, port 9000.

### 7. What does /24 mean in 172.28.20.0/24?

The first 24 bits are the network part, the last 8 bits number the machines. So all
addresses 172.28.20.x are in one network, with 254 usable addresses. 172.28.x.x belongs to
the private addresses, which are not used on the Internet.

### 8. ★ Why TCP and not UDP?

TCP delivers all bytes, in the right order, or reports an error. UDP can lose or reorder
packets. If ciphertext were lost, the message could not be decrypted correctly.

### 9. What is a socket?

The end point of a network connection inside a program. The program sends and receives
bytes through it, similar to writing and reading a file.

### 10. What do ping and tcpdump do?

`ping` checks whether another machine answers. `tcpdump` shows the packets that pass
through a network interface. We use it to show that only ciphertext is sent.

### 11. What are plaintext, ciphertext and key?

Plaintext is the readable message, ciphertext is the encrypted one. The key is the secret
number that controls the encryption. Without it the ciphertext cannot be read.

### 12. ★ Symmetric or asymmetric: what is DES?

Symmetric: the same key encrypts and decrypts, so both machines must know it. Asymmetric
systems such as RSA have two keys, a public and a private one.

### 13. What is a block cipher?

A cipher that encrypts blocks of a fixed size: 64 bits for DES, 128 bits for AES. A stream
cipher encrypts a continuous stream, bit by bit or byte by byte.

### 14. What is XOR and why do ciphers use it?

XOR gives 1 if the two bits are different. It undoes itself: `(x ^ k) ^ k = x`. So the
same operation can be used for encryption and decryption.

### 15. Why do you show everything in hexadecimal?

One hex digit is exactly 4 bits, so 64 bits are 16 digits. It is short, and it is easy to
convert to bits by hand. The handout uses it too.

---

# Level 2: DES in general

### 16. ★ What is DES?

The Data Encryption Standard, a symmetric block cipher. It became a US standard in 1977 and
was withdrawn in 2005. It encrypts 64-bit blocks with a 56-bit key in 16 rounds.

### 17. ★ The key has 64 bits. Why are only 56 used?

Every 8th bit (8, 16, ..., 64) is a parity bit, meant to detect errors in the key.
Permuted choice 1 removes these bits. The key `0e1470c846d8e958` is our key with all 8
parity bits changed, and it gives the same ciphertext. The handout's key does not even have
correct parity, and DES does not care.

### 18. ★ What happens to a block from start to end?

1. Initial permutation (IP)
2. 16 rounds
3. Swap of the two halves
4. Inverse initial permutation (IP^-1)

### 19. ★ What happens in one round?

1. Expand the right half from 32 to 48 bits (E)
2. XOR with the round key
3. S-boxes: 48 bits become 32 bits
4. Permutation P
5. XOR with the left half
6. Swap the halves

As a formula: `L(i) = R(i-1)` and `R(i) = L(i-1) ^ f(R(i-1), K(i))`.

### 20. What is a Feistel cipher?

A cipher that splits the block into two halves. In each round only one half is changed: it
is XORed with a function of the other half and the round key. Because XOR undoes itself,
the function does not have to be reversible, and decryption uses the same algorithm.

### 21. ★ How is decryption different from encryption?

Only the order of the round keys: K16, K15, ..., K1 instead of K1, ..., K16. Everything
else is the same.

### 22. What are confusion and diffusion? Which step gives which?

Confusion hides the relation between key and ciphertext; in DES the S-boxes do this.
Diffusion spreads the influence of every bit over many ciphertext bits; E and P do this
over the rounds.

### 23. What is the avalanche effect?

A change of one bit in the plaintext or the key changes about half of the ciphertext bits.
In the handout's example, plaintext bit 4 changes 32 of the 64 bits, and key bit 4 changes
30. Our DES gives the same numbers.

### 24. ★ Is DES secure today?

No. The key is too short: 2^56 is about 7.2 x 10^16 keys, and all of them can be tried. In
January 1999 a DES key was found publicly in 22 hours and 15 minutes. AES replaced DES.

### 25. How long would trying all keys take?

With one billion keys per second: about 2.3 years for all of them, about half of that on
average. Many computers or special hardware do it in hours or days.

### 26. What is Triple DES? How is AES different?

Triple DES uses DES three times: encrypt with K1, decrypt with K2, encrypt with K3. It is
stronger but slow, and it is being retired. AES has 128-bit blocks, keys of 128, 192 or 256
bits, and is not a Feistel cipher.

---

# Level 3: the DES steps

### 27. What does the initial permutation do? Does it add security?

It only moves the 64 bits to new positions. No key is involved and the table is public, so
it adds no security.

### 28. What does the 58 at the start of the IP table mean?

The first output bit is input bit 58. The second number, 50, means: the second output bit
is input bit 50, and so on. Bit 1 is the leftmost bit.

### 29. What does the inverse initial permutation do?

It undoes IP: `IP^-1(IP(x)) = x`. It is the last step of DES.

### 30. How does the expansion E work, and why is it needed?

It makes 48 bits from 32 by using some bits twice. Every group of 4 bits gets the
neighbouring bit on each side: bits 1-4 become 32 1 2 3 4 5, bits 5-8 become 4 5 6 7 8 9.
It is needed because the round key has 48 bits. It also makes one bit influence two
S-boxes.

### 31. ★ How are the round keys made?

1. PC-1 takes 56 of the 64 key bits and splits them into C0 and D0 (28 bits each).
2. In every round C and D are rotated left by 1 or 2 positions.
3. PC-2 picks 48 of the 56 bits: this is the round key.

### 32. In which rounds is the shift only 1? Why does that matter?

In rounds 1, 2, 9 and 16; in all others it is 2. The sum is 28, the length of a half, so
after round 16 C and D are back at C0 and D0. You can see it in the output: the input in the
last `permuted_choice_2` line is `68fc44a1113e96`, the output of `permuted_choice_1`.

### 33. Which bits does PC-2 leave out?

Bits 9, 18, 22, 25, 35, 38, 43 and 54 of the 56 bits. (For PC-1 it is the parity bits 8,
16, ..., 64.)

### 34. ★ How does an S-box work?

It gets 6 bits. The first and the last bit together are the row (0-3), the four bits in the
middle are the column (0-15). The number in the table is the 4-bit output. Example from
round 1: S1 gets `111001`, so row `11` = 3, column `1100` = 12, output 10 = `1010`.

### 35. Why are the S-boxes the most important part?

They are the only non-linear step. Permutations and XOR are linear; without the S-boxes
the whole cipher could be solved with a system of linear equations.

### 36. An S-box makes 4 bits from 6. How can you decrypt that?

We never reverse an S-box. In a Feistel cipher, decryption computes the same function f
again and XORs it once more, and the two XORs cancel out.

### 37. ★ Why are the halves swapped, and why once more after round 16?

A round changes only one half, so the swap makes sure that both halves are changed in turn.
The extra swap after round 16 undoes the swap of that round. Because of it the same code
can decrypt: only the key order changes.

---

# Level 4: our Docker and network setup

### 38. ★ Explain your Dockerfile line by line.

| Line | Meaning |
|---|---|
| `FROM debian:bookworm-slim` | start with a small Debian 12 system |
| `RUN apt-get ... gcc libc6-dev` | install the C compiler and the C library headers |
| `iproute2 iputils-ping tcpdump` | install `ip`, `ping` and the packet capture tool |
| `rm -rf /var/lib/apt/lists/*` | delete the package lists, so the image is smaller |
| `WORKDIR /lab2` | work in the folder `/lab2` |
| `COPY lab2.c .` | copy our program into the image |
| `RUN gcc -o lab2 lab2.c` | compile it while the image is built |
| `CMD ["sleep", "infinity"]` | what a container runs when it starts |

### 39. ★ Explain your docker-compose.yml.

It has two services, `machine-a` and `machine-b`. Both are built from the Dockerfile in
this folder (`build: .`). Each one has a host name and a fixed IP address on the network
`des_lan`, whose subnet is 172.28.20.0/24.

### 40. What do these commands do?

| Command | Meaning |
|---|---|
| `docker compose up -d --build` | build the images, create the network, start both containers in the background |
| `docker compose exec machine-b ./lab2 server` | run a command inside the running container |
| `docker compose down` | stop and remove the containers and the network (the images stay) |

### 41. ★ How are the two machines connected?

Docker creates a virtual switch (a Linux bridge) for `des_lan`. Each container has a
network card `eth0`, which is connected to the switch by a virtual cable (a veth pair). The
gateway 172.28.20.1 is the host's side of the switch.

### 42. Why do the machines have fixed IP addresses?

The client has to know the address of the server: `./lab2 client 172.28.20.20`. Without
fixed addresses Docker would choose them, and they could change.

### 43. Are these really two computers?

From the program's point of view, yes. Each container has its own host name, network
interface, IP address, processes and file system. They share the hardware and the Linux
kernel. (Linux calls this isolation "namespaces".)

### 44. Why does the container run `sleep infinity`?

A container stops when its main program ends. `sleep` keeps it running, so that we can
start `lab2` by hand with `exec` and type messages.

### 45. What does `init: true` do?

It starts a tiny init process as process number 1, which passes on the stop signal. Without
it `sleep` would ignore the signal and `docker compose down` would wait 10 seconds before
killing it.

### 46. Can somebody outside connect to port 9000?

Not through a port of the host: we have no `ports:` entry, so the port is not published.
Only machines on `des_lan` and the host itself can reach it.

### 47. How would you run this on two real computers?

Both must be in the same network. Compile `lab2.c` on both with `gcc`. Start
`./lab2 server` on one and allow TCP port 9000 in its firewall. Start
`./lab2 client <IP address of the server>` on the other. Nothing in the program depends on
Docker. It needs Linux (on Windows: WSL), because it uses POSIX sockets. We tested it on two
containers, not on two physical computers.

### 48. ★ What do we see in your packet capture?

Two packets per message. The first has 4 bytes, `0000 0028`: the length, 40. The second has
40 bytes: the ciphertext. In its line `0x0030`, after the first 4 bytes (the end of the TCP
header), you can read `9f1b d790 86a5 ccbc`. That is the first block of the `[ENCRYPT]`
line. The text of the message is nowhere. The TCP handshake is not shown because we
captured only packets that carry data.

---

# Level 5: our code

### 49. ★ How is your program organised?

One file, 446 lines, in four parts: the DES tables, the DES steps, the messages, `main`.
Every DES step is its own function:

| Lab item | Function |
|---|---|
| 2.1 | `initial_permutation` |
| 2.2 | `inverse_initial_permutation` |
| 2.3 | `expansion_permutation` |
| 2.4 | `generate_round_keys`, with `permuted_choice_1`, `left_circular_shift`, `permuted_choice_2` |
| 2.5 | `xor_round_key` |
| 2.6 | `sbox_substitution` |
| 2.7 | `permutation_p` |
| 2.8 | `xor_left_half` |
| 2.9 | `swap_halves` |
| 2.10 | `create_message`, `encrypt_message`, `send_message` |
| 2.11 | `receive_message`, `decrypt_message`, `display_message` |

`des()` calls the steps in the right order, and `chat()` takes the turns.

### 50. Why are server and client the same program?

Both need the same DES code and the same message functions. The first argument selects the
role: `./lab2 server` or `./lab2 client ADDRESS`. `./lab2 steps` shows the DES steps.

### 51. What is `u64`, and why is it unsigned?

A short name for `unsigned long long`, a 64-bit number, so a whole block fits into one
variable. It is unsigned because then `>>` fills up with zeros; with a signed number it
could fill up with ones.

### 52. ★ Explain `permute()`.

```c
output = (output << 1) | ((input >> (input_bits - table[i])) & 1);
```

- `table[i]` is the number of the input bit we want, counted from the left.
- `input >> (input_bits - table[i])` moves this bit to the far right. For bit 58 of 64 the
  shift is 6.
- `& 1` keeps only this bit.
- `output << 1` makes room on the right, and `|` puts the bit there.

All six permutations (IP, IP^-1, E, P, PC-1, PC-2) use this function with their own table.

### 53. What is `show`?

A switch. With `./lab2 steps` it is 1, and every step function prints its input and its
output. In the chat it is 0, so nothing is printed. It does not change the result.

### 54. Explain `left_circular_shift()`.

```c
u64 out = ((half << n) | (half >> (28 - n))) & 0xfffffff;
```

`half << n` shifts left, `half >> (28 - n)` brings the bits that fell out back on the right.
`0xfffffff` is 28 ones; the `&` removes everything above 28 bits.

### 55. ★ Explain `sbox_substitution()`.

```c
int six = (input >> (42 - 6 * i)) & 63;
int row = ((six >> 4) & 2) | (six & 1);
int col = (six >> 1) & 15;
out = (out << 4) | S[i][row][col];
```

- `six`: the 6 bits of box `i`. For the first box the shift is 42, so the leftmost 6 of the
  48 bits. 63 is `111111`.
- `row`: the first bit (moved to the place of the 2) together with the last bit.
- `col`: the four bits in the middle. 15 is `1111`.
- The 4-bit result is appended to `out`.

### 56. ★ Explain `des()`. Where is the difference between encryption and decryption?

It makes the 16 round keys, does IP, then 16 rounds (E, XOR, S-boxes, P, XOR with left,
swap), one more swap and IP^-1. The only difference is this expression:

```c
decrypt ? k[17 - i] : k[i]
```

In round 1 it takes K1 for encryption and K16 for decryption.

### 57. Why does the array of round keys have 17 elements?

So that `k[1]` is K1 and `k[16]` is K16, as in the textbook. `k[0]` is not used.

### 58. How does a text become blocks?

`get_block()` joins 8 characters into one 64-bit number; the first character is on the left.
"Hello Ma" becomes `48656c6c6f204d61`. `put_block()` does the opposite.

### 59. Why is there `& 255` in `get_block()`?

`char` is signed here, so bytes above 127 (as in Turkish letters) are negative. Without
`& 255` the number would be filled with ones on the left, and the block would be wrong.

### 60. What does `(strlen(text) / 8 + 1) * 8` do?

It computes how many bytes are encrypted: the next multiple of 8 above the length. The rest
of the last block is filled with zeros.

| Characters | Bytes sent |
|---|---|
| 0 | 8 |
| 7 | 8 |
| 8 | 16 |
| 35 ("Hello Machine B, this is Machine A.") | 40 |

There is always at least one zero byte, so the receiver knows where the text ends.

### 61. ★ Why do you send the length before the ciphertext?

TCP is a stream of bytes without message boundaries. The receiver must know how many bytes
belong to the message. `strlen` cannot be used, because ciphertext can contain zero bytes.

### 62. What do `htonl`, `MSG_WAITALL` and the check of `n` do?

- `htonl` puts the length into network byte order (big-endian), and `ntohl` converts it
  back. Computers can store numbers in different byte orders.
- `MSG_WAITALL` waits until all `n` bytes have arrived. Normally `recv` can return only a
  part.
- The check `n <= 0 || n > MAX` protects the buffer. Without it a wrong length could
  overwrite memory (buffer overflow).

### 63. Explain the network part of `main`.

| Machine B (server) | Machine A (client) |
|---|---|
| `socket`: create the end point | `socket` |
| `bind`: take port 9000 | |
| `listen`: wait for connections | |
| `accept`: take the first connection | `connect`: connect to the address and port 9000 |
| `chat(sock, 0)`: receives first | `chat(sock, 1)`: sends first |

`INADDR_ANY` (0.0.0.0) means all network interfaces. `SO_REUSEADDR` lets the server start
again immediately on the same port.

### 64. ★ What did you change in the starter code, and why?

| Starter code | Problem | Our program |
|---|---|---|
| two programs | the same code would be needed twice | one program, two roles |
| server on 127.0.0.1 | only the same computer can connect | 0.0.0.0, all interfaces |
| client has the address 127.0.0.1 | cannot reach another computer | address is an argument |
| `scanf("%s")` | stops at the first space, no length limit | `fgets` reads a whole line |
| `strlen` for the length | ciphertext can contain zero bytes | the length is sent first |
| one `recv` | may return a part of a message | `MSG_WAITALL` |
| `fork` for every client | not needed | one connection, two machines |

The report names the four main ones: one program, all interfaces, the length first, whole
lines. We also added DES: encryption before sending, decryption after receiving.

---

# Level 6: hard questions

### 65. ★ Which mode of operation do you use? What is its weakness?

ECB: every 8-byte block is encrypted on its own. The weakness is that equal blocks give
equal ciphertext. The message `AAAAAAAAAAAAAAAA` gives
`3f72ec88c27be0b6 3f72ec88c27be0b6 0708f6a0c5751769`: the first two blocks are the same.
And the same message sent twice gives the same ciphertext. CBC with a random start value
(IV) would hide both.

### 66. ★ What happens if the two machines have different keys?

The message arrives, but the other side displays garbage. There is no error message, because
the program cannot know that the key is wrong.

### 67. ★ Where is the key? Is that a good idea?

It is a constant in `lab2.c` on both machines and is never sent. That is fine for the lab,
but anybody who has the program has the key. Real systems agree on a new key for every
connection, for example with Diffie-Hellman or RSA, as TLS does.

### 68. What can somebody who listens on the network still learn?

Who talks to whom, when, how long the messages are (in steps of 8 bytes), and whether a
block or a message is repeated. Not the text itself.

### 69. What happens if somebody changes one bit of the ciphertext?

That 8-byte block becomes garbage. Example: `da02ce3a89ecac3a` (last bit changed) decrypts to
`08b8c1539d741138` instead of `02468aceeca86420`, and 34 of the 64 bits are wrong. The program
does not notice it. DES gives confidentiality but no integrity; for that you need a MAC
(message authentication code).

### 70. Can somebody send a recorded message again (replay)?

With this program, yes: nothing in a message says that it is new. A message number
protected by a MAC would help.

### 71. What happens with a message of exactly 8 characters?

16 bytes are sent: the 8 characters and one block of zeros. The block of zeros always has
the same ciphertext, `0708f6a0c5751769`, because we use ECB.

### 72. Why can you not send a file with zero bytes in it?

We fill the last block with zeros, and the text ends at the first zero byte. So the receiver
cannot tell zeros of the message from filling. PKCS#7 padding solves this: it fills with the
number of added bytes.

### 73. What happens with a message longer than 1023 characters?

`fgets` reads 1023 characters. The rest stays in the input and is sent as the next message
at the next turn, without waiting for the keyboard. We tried it with 1500 characters: the
other side displayed 1023 and then 477.

### 74. What happens if you start the client first? Or the server twice?

The client stops with `client: Connection refused`. A second server stops with
`server: Address already in use`.

### 75. What happens if a second client connects?

It is connected, because the operating system keeps it in the waiting queue, but our server
calls `accept` only once and never reads its message. When the server ends, the second
client ends too.

### 76. What happens if one side is closed with Ctrl-C?

If the other side is waiting, it prints "The conversation is over.". If the other side is
typing, its program ends without a message when it sends, because sending on a closed
connection raises the signal SIGPIPE. Better would be `send` with `MSG_NOSIGNAL` and a check
of its result.

### 77. Why can only one side type at a time?

`chat()` takes turns: send, receive, send, receive. For typing at any time the program would
need two threads, or `select`/`poll` to watch the keyboard and the socket together.

### 78. ★ How do you know that your DES is correct?

- All 16 round keys and all halves are the same as in the handout's Table 4.2.
- Decrypting the ciphertext gives the plaintext again.
- OpenSSL gives the same ciphertext (question 91).

The handout itself has three typing errors: in K6 and K7 the letter l is printed instead of
the digit 1, and the last row shows `25896490` (which is R16) instead of `da02ce3a`.

### 79. ★ The lab sheet asks for debugger screenshots in step mode. Where are they?

This is probably the most critical question, so be honest. Suggested answer: "We print the
input and the output of every step function instead. These are the variables one would watch
in the debugger, and the screenshots show the code together with the values. We can also
step through it now if you want." For that, compile with `gcc -g -o lab2 lab2.c`, set a
breakpoint on the `return out;` line of a step function and watch `out`. Practise it once.

### 80. What would you improve?

- CBC with a random IV instead of ECB
- A key that is not in the source code, and a key exchange
- A MAC, so that changed or repeated messages are noticed
- AES instead of DES
- Make the round keys once; now `des()` makes them again for every block
- Both sides can type at any time

---

# Level 7: "do it in front of me"

### 81. Compute the first byte of IP by hand.

The plaintext is `02 46 8a ce ec a8 64 20`. The first row of the IP table is 58 50 42 34 26
18 10 2. That is the second bit of every byte, from the last byte to the first:

| Byte | 20 | 64 | a8 | ec | ce | 8a | 46 | 02 |
|---|---|---|---|---|---|---|---|---|
| bits | `00100000` | `01100100` | `10101000` | `11101100` | `11001110` | `10001010` | `01000110` | `00000010` |
| second bit | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 |

`01011010` = `5a`, the first byte of `5a005a00 3cf03c0f`.

### 82. ★ Follow the first S-box of round 1 by hand.

1. R0 = `3cf03c0f` = `0011 1100 ... 1111`. E takes bits 32, 1, 2, 3, 4, 5: `1 0 0 1 1 1`.
2. K1 = `7833c320da70`; its first 6 bits are `011110`.
3. XOR: `100111 ^ 011110 = 111001`.
4. S1: row `11` = 3, column `1100` = 12, value 10 = `1010` = `a`.
5. `a` is the first digit of the S-box output `a32f11c2`.

### 83. Rotate C0 = 68fc44a left by one position.

`0110 1000 1111 1100 0100 0100 1010`. The first bit (0) goes to the end:
`1101 0001 1111 1000 1000 1001 0100` = `d1f8894` = C1.

### 84. Compute R1.

R1 = L0 ^ f = `5a005a00 ^ e0d27245`. Digit by digit: 5^e = b, a^0 = a, 0^d = d, 0^2 = 2,
5^7 = 2, a^2 = 8, 0^4 = 4, 0^5 = 5. So R1 = `bad22845`.

### 85. Your K1 is 7833c320da70, but the handout shows 1e030f03080d2930. Why?

It is the same key. The handout writes every group of 6 bits as two hex digits:

| 6 bits | `011110` | `000011` | `001111` | `000011` | `001000` | `001101` | `101001` | `110000` |
|---|---|---|---|---|---|---|---|---|
| hex | 1e | 03 | 0f | 03 | 08 | 0d | 29 | 30 |

### 86. Change the key or the port.

Key: the line `u64 key = 0x0f1571c947d9e859;`. Port: `#define PORT 9000`. Then run
`docker compose up -d --build`, because the program is compiled when the image is built.
Both machines get the new program.

### 87. Show only round 16.

```sh
./lab2 steps | grep -A 14 'round 16 '
```

### 88. ★ Change the program from ECB to CBC.

In `encrypt_message()` replace the loop:

```c
    u64 previous = 0;
    for (int i = 0; i < length; i += 8) {
        previous = des(get_block(text + i) ^ previous, 0);
        put_block(previous, cipher + i);
    }
```

In `decrypt_message()` replace the loop:

```c
    u64 previous = 0;
    for (int i = 0; i < length; i += 8) {
        u64 c = get_block(cipher + i);
        put_block(des(c, 1) ^ previous, text + i);
        previous = c;
    }
```

Every block is XORed with the ciphertext block before it, so equal blocks become different.
Here the start value (IV) is 0, so the same message twice still gives the same ciphertext. A
complete version would use a random IV for every message and send it along.

### 89. Read the key from outside instead of from the source code.

Add `#include <stdlib.h>` at the top and these lines in `main`, before
`if (argc == 2 && strcmp(argv[1], "steps") == 0)`:

```c
    if (getenv("DES_KEY"))
        key = strtoull(getenv("DES_KEY"), NULL, 16);
```

Then: `DES_KEY=133457799bbcdff1 ./lab2 steps`.

### 90. How would you build Triple DES from your functions?

```c
key = k1; block = des(block, 0);      /* encrypt with K1 */
key = k2; block = des(block, 1);      /* decrypt with K2 */
key = k3; block = des(block, 0);      /* encrypt with K3 */
```

### 91. Prove that your ciphertext is correct and that only ciphertext is sent.

OpenSSL, on the host (prints `da02ce3a89ecac3b`):

```sh
printf '\x02\x46\x8a\xce\xec\xa8\x64\x20' | openssl enc -des-ecb -K 0f1571c947d9e859 \
    -nopad -provider legacy -provider default | xxd -p
```

The packets, in a third terminal while the two machines talk:

```sh
docker compose exec machine-b tcpdump -i eth0 -nn -X tcp port 9000
```

---

# Before the evaluation

1. Both team members should be able to explain everything. Agree on who answers what if the
   evaluator asks "Who did which part?".
2. Run the demo once on the computer you will use:

   ```sh
   cd 3rdtimesthecharm
   docker compose up -d --build
   docker compose exec machine-a ./lab2 steps                  # the DES steps
   docker compose exec machine-b ./lab2 server                 # terminal 1
   docker compose exec machine-a ./lab2 client 172.28.20.20    # terminal 2
   docker compose down
   ```

3. Have `lab2.c` open in an editor, so that you can point to a line while you explain it.
4. If you do not know an answer, say what you do know and show it with `./lab2 steps`. Do
   not guess.
