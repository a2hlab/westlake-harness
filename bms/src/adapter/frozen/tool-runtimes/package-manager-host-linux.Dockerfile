FROM ubuntu@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        g++=4:11.2.0-1ubuntu1 \
        libminizip-dev=1.1-8build1 \
        libssl-dev=3.0.2-0ubuntu1.25 \
        zlib1g-dev=1:1.2.11.dfsg-2ubuntu9.2 \
    && rm -rf /var/lib/apt/lists/*

LABEL org.opencontainers.image.title="WestLake package-manager host regression"
LABEL org.opencontainers.image.source="src/adapter/frozen/tool-runtimes/package-manager-host-linux.Dockerfile"
LABEL org.opencontainers.image.version="20260727"
