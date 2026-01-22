FROM debian:latest
LABEL maintainer="Alexis DANJON <alexis.danjon@nc3.lu>"

ARG DEPLOYER_CLI_CONFIG_USER=range42-operator
ENV DEPLOYER_CLI_CONFIG_USER=${DEPLOYER_CLI_CONFIG_USER}

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -q update \
    && apt-get -qy --no-install-recommends install \
    sudo \
    git \
    yq \
    pwgen \
    keychain \
    curl \
    vim \
    ansible \
    python3 \
    # ssh-add \
    # ssh-keygen \
    # ssh-copy-id \
    && apt-get -qy --purge autoremove \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash "$DEPLOYER_CLI_CONFIG_USER" && \
    echo "$DEPLOYER_CLI_CONFIG_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/"$DEPLOYER_CLI_CONFIG_USER" && \
    chmod 0440 /etc/sudoers.d/"$DEPLOYER_CLI_CONFIG_USER"

WORKDIR /home/$DEPLOYER_CLI_CONFIG_USER

USER $DEPLOYER_CLI_CONFIG_USER

COPY range42 ./range42

# ENTRYPOINT ["python3", "-m", "range42"]
