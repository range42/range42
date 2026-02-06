FROM python:slim

ENV DEBIAN_FRONTEND=noninteractive
ENV ANSIBLE_FORCE_COLOR=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    git \
    ca-certificates \
    curl \
    jq \
    sudo \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    ansible-core \
    ansible-lint \
    jmespath \
    netaddr \
    passlib \
    requests \
    proxmoxer \
    bcrypt

ARG USER=user
ARG UID=1000
ARG GID=1000

RUN groupadd -g ${GID} ${USER} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
 && echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} \
 && chmod 0440 /etc/sudoers.d/${USER}

USER ${USER}
WORKDIR /home/${USER}

COPY --chown=$USER:$USER ansible .
COPY --chown=$USER:$USER docker/entrypoint.sh /entrypoint.sh

RUN ansible-galaxy collection install -r requirements.yml \
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
