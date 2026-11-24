# One image for both machines: the C compiler, the network tools and the program.
FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev iproute2 iputils-ping tcpdump \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /lab2
COPY lab2.c .
RUN gcc -o lab2 lab2.c
CMD ["sleep", "infinity"]
