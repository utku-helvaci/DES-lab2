# Lab 2 - DES on Two Computers (CMPE455/CMSE456)

## Run on two machines (Docker)

```sh
docker compose up -d --build                                # start machine-a and machine-b
docker compose exec machine-b ./lab2 server                 # terminal 1: Machine B (server)
docker compose exec machine-a ./lab2 client 172.28.20.20    # terminal 2: Machine A (client)
docker compose down                                         # stop both machines
```

The client sends first; then the two sides take turns. `:exit` (or Ctrl-D) ends the
conversation. Both machines know the key: it is a constant in `lab2.c`.

## DES step tables

```sh
gcc -o lab2 lab2.c    # or use the executable lab2 in this folder (Linux, x86-64)
./lab2 steps          # every DES step of the handout example:
                      # key 0f1571c947d9e859, plaintext 02468aceeca86420
```
