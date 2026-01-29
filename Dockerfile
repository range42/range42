FROM debian:testing-slim

ARG DEPLOYER_USER=user
ENV DEPLOYER_USER=${DEPLOYER_USER}
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo \
        ansible \
        python3 \
        python3-pip \
        openssh-server \
        sshpass \
        ca-certificates \
        build-essential \
    && ssh-keygen -A \
    && useradd -m -s /bin/bash "$DEPLOYER_USER" \
    && echo "$DEPLOYER_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/"$DEPLOYER_USER" \
    && chmod 0440 /etc/sudoers.d/"$DEPLOYER_USER" \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/$DEPLOYER_USER/
COPY --chown=$DEPLOYER_USER:$DEPLOYER_USER . ./range42

USER $DEPLOYER_USER
ENV PATH=/home/$DEPLOYER_USER/.local/bin:$PATH

RUN cd range42 \
    && pip3 install --break-system-packages --upgrade pip \
    && pip3 install --break-system-packages . \
    && rm -rf ~/.cache/pip ~/range42

USER root
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
