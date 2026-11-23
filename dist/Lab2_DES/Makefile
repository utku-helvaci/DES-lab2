# Makefile - CMPE455/CMSE456 Lab 2: DES on two computers
#
#   make            build everything into bin/
#   make test       unit tests of every DES step + known-answer tests
#   make check      test + cross-check against pycryptodome/OpenSSL + loopback chat
#   make demo       two Docker "machines" exchange encrypted messages
#   make report / make reduced-report    the full or the reduced lab report
#   make dist [REPORT=full|reduced|both] the submission zip
#   make clean
#
# -O0 -g3 on purpose: every local variable stays visible in the debugger,
# which the lab needs for the step-mode screenshots.

CC       ?= gcc
CFLAGS   ?= -std=c11 -Wall -Wextra -Wpedantic -O0 -g3
CPPFLAGS += -D_DEFAULT_SOURCE -Isrc
BIN      := bin
# report put into the zip by `make dist`: full, reduced or both
REPORT   ?= full

CORE    := src/des.c src/des_trace.c src/des_util.c src/des_modes.c
CHAT    := src/net.c src/des_chat.c
HEADERS := $(wildcard src/*.h)

PROGRAMS := $(BIN)/tcpServer $(BIN)/tcpClient $(BIN)/des_trace \
            $(BIN)/des_avalanche $(BIN)/des_test

.PHONY: all test crosscheck loopback check demo examples screenshots report reduced-report \
        dist clean

all: $(PROGRAMS)

$(BIN):
	mkdir -p $(BIN)

$(BIN)/tcpServer: src/tcpServer.c $(CORE) $(CHAT) $(HEADERS) | $(BIN)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/tcpServer.c $(CORE) $(CHAT)

$(BIN)/tcpClient: src/tcpClient.c $(CORE) $(CHAT) $(HEADERS) | $(BIN)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/tcpClient.c $(CORE) $(CHAT)

$(BIN)/des_trace: src/des_trace_main.c $(CORE) $(HEADERS) | $(BIN)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/des_trace_main.c $(CORE)

$(BIN)/des_avalanche: src/des_avalanche.c $(CORE) $(HEADERS) | $(BIN)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/des_avalanche.c $(CORE)

$(BIN)/des_test: tests/test_des.c $(CORE) $(HEADERS) | $(BIN)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ tests/test_des.c $(CORE)

test: $(BIN)/des_test
	./$(BIN)/des_test

crosscheck: $(BIN)/des_trace
	python3 tests/crosscheck.py

loopback: $(BIN)/tcpServer $(BIN)/tcpClient
	./tests/test_loopback.sh

check: test crosscheck loopback

demo:
	./docker/demo.sh

clean:
	rm -rf $(BIN)

examples: all
	./tools/make_examples.sh

screenshots: all
	python3 tools/screenshots.py all

report: all
	python3 report/make_figures.py
	python3 report/build_report.py

reduced-report: all
	python3 report/make_figures.py
	python3 report/build_reduced_report.py

dist:
	REPORT=$(REPORT) ./tools/package.sh
