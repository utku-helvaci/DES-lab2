# docker/Dockerfile - ONE image used for BOTH computers (machine-a, machine-b).
#
# Stage 1 compiles the programs and runs the unit tests (the build fails if a
# DES step is wrong).  Stage 2 is the "computer": the executables plus the
# usual network tools (ip, ping, tcpdump) and gdb for debugging on a machine.

FROM debian:bookworm-slim AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/des-lab
COPY Makefile ./
COPY src ./src
COPY tests ./tests
RUN make bin/tcpServer bin/tcpClient bin/des_trace bin/des_avalanche bin/des_test \
 && ./bin/des_test

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends iproute2 iputils-ping tcpdump gdb procps \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/des-lab
COPY --from=build /opt/des-lab/bin/ ./bin/
COPY src ./src
COPY test_examples/messages_machine_a.txt test_examples/messages_machine_b.txt ./test_examples/
ENV PATH="/opt/des-lab/bin:${PATH}"
CMD ["sleep", "infinity"]
