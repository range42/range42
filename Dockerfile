FROM debian:testing-slim
LABEL maintainer="Alexis DANJON <alexis.danjon@nc3.lu>"

ARG DEPLOYER_USER=user
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
        python3-pip \
        openssh-server \
        sshpass \
    && ssh-keygen -A \
    && apt-get -qy --purge autoremove \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash "$DEPLOYER_USER" && \
    echo "$DEPLOYER_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/"$DEPLOYER_USER" && \
    chmod 0440 /etc/sudoers.d/"$DEPLOYER_USER"

WORKDIR /home/$DEPLOYER_USER
USER $DEPLOYER_USER

COPY --chown=$DEPLOYER_USER:$DEPLOYER_USER range42 ./range42
COPY --chown=$DEPLOYER_USER:$DEPLOYER_USER requirements.txt ./requirements.txt

RUN pip3 install --break-system-packages -r requirements.txt && rm requirements.txt

CMD sudo /usr/sbin/sshd & exec su - $DEPLOYER_USER
# ENTRYPOINT ["python3", "-m", "range42"]
