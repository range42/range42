"""Keep the SSH keepalive in both ansible.cfg files.

Without ServerAliveInterval, a peer that dies without FIN/RST (a guest that
reboots during a command) leaves the multiplexed session open forever and the
play hangs. Setting ssh_args replaces Ansible's default, so the default
ControlMaster options must stay in the value.
"""
import configparser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [
    ROOT / "ansible.cfg",
    ROOT / "roles/deployer.bootstrap/templates/ansible.cfg.j2",  # no Jinja expressions
]


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.name)
def test_ssh_args_keep_mux_defaults_and_set_keepalive(path):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read_string(path.read_text())
    ssh_args = cfg.get("ssh_connection", "ssh_args", fallback="").split()
    for option in ("ControlMaster=auto", "ControlPersist=60s",
                   "ServerAliveInterval=30", "ServerAliveCountMax=4"):
        assert option in ssh_args, f"{path.name}: {option} missing from ssh_args"
