FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates cmake ninja-build clang build-essential python3 openjdk-21-jdk-headless \
    zlib1g-dev nlohmann-json3-dev git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libclang-rt-18-dev && rm -rf /var/lib/apt/lists/*
