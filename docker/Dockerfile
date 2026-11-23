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
# Makefile, src/, tests/ and the two message scripts of test_examples/: .dockerignore
# lets nothing else in. The zip of the reduced report has no tests/ and no
# test_examples/; make then leaves out bin/des_test, and there is nothing to run.
COPY . ./
RUN make \
 && if [ -x bin/des_test ]; then ./bin/des_test; fi \
 && mkdir -p test_examples

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends iproute2 iputils-ping tcpdump gdb procps \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/des-lab
COPY --from=build /opt/des-lab/bin/ ./bin/
COPY --from=build /opt/des-lab/src/ ./src/
COPY --from=build /opt/des-lab/test_examples/ ./test_examples/
ENV PATH="/opt/des-lab/bin:${PATH}"
CMD ["sleep", "infinity"]
