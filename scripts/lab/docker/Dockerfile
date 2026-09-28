# a2hlab build image: the a2hlab VM's build userland (Ubuntu 24.04 amd64 under Rosetta, uid 501) without
# its state. Toolchains (OH clang-15, JDK 21, android build-tools) come from the bind-mounted workspace,
# not from this image, so the image never changes what gets built. See tools/dockbuild.sh.
FROM ubuntu:24.04
# GitHub/archive.ubuntu.com are flaky from here; the huaweicloud mirror is reliable (OPS-RUNBOOK §1).
RUN sed -i -e 's#http://archive.ubuntu.com/ubuntu#http://mirrors.huaweicloud.com/ubuntu#g' \
           -e 's#http://security.ubuntu.com/ubuntu#http://mirrors.huaweicloud.com/ubuntu#g' \
           /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential ccache git git-lfs curl ca-certificates file make patch rsync \
      unzip zip xz-utils zstd bzip2 python3 python3-yaml python3-venv util-linux xxd sudo \
 && rm -rf /var/lib/apt/lists/*
# Same uid/gid as the VM user, so files written into the shared workspace keep their owner.
RUN (userdel -r ubuntu 2>/dev/null || true) \
 && groupadd -g 501 zhaoyue && useradd -u 501 -g 501 -m -d /home/zhaoyue -s /bin/bash zhaoyue \
 && echo 'zhaoyue ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/zhaoyue
USER zhaoyue
ENV HOME=/home/zhaoyue
