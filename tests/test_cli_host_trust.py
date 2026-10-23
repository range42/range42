"""Ordinary native Ansible refuses unknown and stale guest generations."""
import io
import logging
import os
import socket
import subprocess
import threading
from pathlib import Path

import paramiko
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('relative', ['ansible.cfg', 'roles/deployer.bootstrap/templates/ansible.cfg.j2'])
@pytest.mark.parametrize('trust', ['unknown', 'stale', 'independently-enrolled'])
def test_actual_ansible_guest_transport_requires_verified_current_pin(tmp_path, relative, trust):
    logging.getLogger('paramiko').setLevel(logging.CRITICAL)
    private = ed25519.Ed25519PrivateKey.generate()
    key = paramiko.Ed25519Key.from_private_key(io.StringIO(private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, serialization.NoEncryption()).decode()))
    public = private.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()
    stopped, executed = threading.Event(), threading.Event()
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(5)
    listener.settimeout(0.2)
    port = listener.getsockname()[1]

    class Server(paramiko.ServerInterface):
        def check_auth_none(self, _username):
            return paramiko.AUTH_SUCCESSFUL

        def check_channel_request(self, kind, _channel):
            return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        def check_channel_pty_request(self, *_args):
            return True

        def check_channel_exec_request(self, _channel, _command):
            executed.set()
            return True

    def serve():
        while not stopped.is_set():
            try:
                client, _ = listener.accept()
            except TimeoutError:
                continue
            transport = paramiko.Transport(client)
            try:
                transport.add_server_key(key)
                transport.start_server(server=Server())
                channel = transport.accept(2)
                if channel is not None and executed.wait(2):
                    channel.send_exit_status(0)
                    channel.close()
                    transport.join(timeout=3)
            except (EOFError, OSError, paramiko.SSHException):
                pass
            finally:
                transport.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    pins = tmp_path / 'known_hosts'
    pin = public
    if trust == 'stale':
        pin = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()
    before = '' if trust == 'unknown' else f'[127.0.0.1]:{port} {pin}\n'
    pins.write_text(before)
    config = tmp_path / 'ansible.cfg'
    config.write_text((ROOT / relative).read_text())
    inventory = tmp_path / 'inventory.yml'
    inventory.write_text(f'all:\n  hosts:\n    guest:\n      ansible_host: 127.0.0.1\n      ansible_port: {port}\n'
                         '      ansible_user: fixture\n      ansible_become: false\n')
    playbook = tmp_path / 'play.yml'
    playbook.write_text('- hosts: all\n  gather_facts: false\n  tasks:\n    - ansible.builtin.raw: "true"\n')
    env = {key: value for key, value in os.environ.items() if not key.startswith('ANSIBLE_')}
    env.update(ANSIBLE_CONFIG=str(config), ANSIBLE_STDOUT_CALLBACK='default', ANSIBLE_NOCOLOR='1',
               ANSIBLE_SSH_RETRIES='0', ANSIBLE_SSH_CONTROL_PATH='none',
               ANSIBLE_SSH_COMMON_ARGS=f'-F /dev/null -o UserKnownHostsFile={pins} '
               '-o GlobalKnownHostsFile=/dev/null -o BatchMode=yes')
    try:
        result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(playbook)],
                                env=env, capture_output=True, text=True, timeout=15, check=False)
    finally:
        stopped.set()
        thread.join(timeout=4)
        listener.close()
    assert (result.returncode == 0) is (trust == 'independently-enrolled'), result.stdout + result.stderr
    assert executed.is_set() is (trust == 'independently-enrolled')
    assert pins.read_text() == before
