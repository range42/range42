"""Keep `range42-context ssh` usable after the known_hosts flush."""
import os
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[1] / "roles/deployer.bootstrap/files/range42-context.sh"


def test_ssh_accepts_a_new_host_key_without_a_prompt(tmp_path):
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    argv_file = tmp_path / "argv"
    (home / ".ssh").mkdir(parents=True)
    bin_dir.mkdir()
    (home / ".ssh/config").write_text("Host r42.x\n    Hostname 192.0.2.10\n")
    stub = bin_dir / "ssh"
    stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{argv_file}"\n')
    stub.chmod(0o755)
    env = {**os.environ, "HOME": str(home), "RANGE42_QUIET": "1",
           "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run(["zsh", "-f", "-c", f'source "{SCRIPT}"\n_r42_ssh x'], env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert argv_file.read_text().splitlines() == ["-o", "StrictHostKeyChecking=accept-new", "r42.x"]
