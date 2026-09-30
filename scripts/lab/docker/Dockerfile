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
# Same user name, uid/gid and home as the VM user, so files written into the shared workspace keep their
# owner and the VM's ~/a2hlab paths hold in the container. dockbuild.sh image passes the VM user's values.
ARG LAB_USER=lab
ARG LAB_UID=501
ARG LAB_GID=501
ARG LAB_HOME=/home/${LAB_USER}
RUN (userdel -r ubuntu 2>/dev/null || true) \
 && groupadd -g "${LAB_GID}" "${LAB_USER}" \
 && useradd -u "${LAB_UID}" -g "${LAB_GID}" -m -d "${LAB_HOME}" -s /bin/bash "${LAB_USER}" \
 && echo "${LAB_USER} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${LAB_USER}"
USER ${LAB_USER}
ENV HOME=${LAB_HOME}
