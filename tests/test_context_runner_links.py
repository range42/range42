"""Keep native context selection compatible with an attempt-owned repository."""
import json
import os
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[1] / "roles/deployer.bootstrap/files/range42-context.sh"


def select_context(tmp_path, *, managed=False, failed_link=False, explicit_config=False, pinned=False):
    home = tmp_path / "home"
    workspace = home / "range42.config/lab-demo"
    checkout = home / "range42"
    for path in (home / ".ssh", workspace / "secrets", checkout / "range42-ansible_roles-debug-devkit",
                 checkout / "range42-playbooks/scenarios/demo", checkout / "range42"):
        path.mkdir(parents=True, exist_ok=True)
    (home / ".ssh/config").write_text("")
    (home / ".zshrc").write_text("")
    (workspace / "sourced_range42.sh").write_text(f'export RANGE42_GITDIR__ROOT_DIR="{checkout}"\n')
    (workspace / "scenario").symlink_to(checkout / "range42-playbooks/scenarios/demo")
    if pinned:
        manifest = checkout / "range42-playbooks/scenarios/demo/manifest"
        manifest.mkdir()
        (manifest / "scenario_vms.json").write_text(json.dumps({"vms": [{"ip": "192.0.2.10"}]}))
        (home / ".ssh/known_hosts").write_text("192.0.2.10 ssh-ed25519 fixture-public-key\n")
    (checkout / "range42/ansible.cfg").write_text("[defaults]\nhost_key_checking = False\n")
    strict = home / "strict.cfg"
    strict.write_text("[defaults]\nhost_key_checking = True\n")
    env = {**os.environ, "HOME": str(home), "RANGE42_QUIET": "1",
           "RANGE42_CONFIG_BASE_DIR": str(home / "range42.config"),
           "RANGE42_CONTEXT_REPO_LINKS_MANAGED": "YES" if managed else "NO"}
    env.pop("ANSIBLE_CONFIG", None)
    if explicit_config:
        env["ANSIBLE_CONFIG"] = str(strict)
    commands = [f'source "{SCRIPT}"', "_r42_ssh_reload() { return 0; }",
                "_r42_status() { return 0; }"]
    if failed_link:
        commands.append("ln() { return 44; }")
    commands += ["range42-context use lab demo || exit $?", 'print -r -- "CONFIG=$ANSIBLE_CONFIG"']
    result = subprocess.run(["zsh", "-f", "-c", "\n".join(commands)], env=env,
                            capture_output=True, text=True, timeout=15)
    return result, checkout, workspace, strict


def test_runner_owned_links_do_not_change_the_installed_repositories(tmp_path):
    result, checkout, _, _ = select_context(tmp_path, managed=True)
    assert result.returncode == 0, result.stderr
    assert not (checkout / "range42-ansible_roles-debug-devkit/secrets").is_symlink()
    assert not (checkout / "range42-playbooks/scenarios/demo/secrets").is_symlink()


def test_failed_native_link_does_not_report_success(tmp_path):
    result, _, _, _ = select_context(tmp_path, failed_link=True)
    assert result.returncode != 0


def test_managed_context_preserves_explicit_ansible_configuration(tmp_path):
    result, _, _, strict = select_context(tmp_path, managed=True, explicit_config=True)
    assert result.returncode == 0, result.stderr
    assert f"CONFIG={strict}" in result.stdout


def test_cli_context_replaces_inherited_ansible_configuration(tmp_path):
    result, checkout, _, _ = select_context(tmp_path, explicit_config=True)
    assert result.returncode == 0, result.stderr
    assert f"CONFIG={checkout / 'range42/ansible.cfg'}" in result.stdout


def test_managed_context_retains_verified_guest_pins(tmp_path):
    result, checkout, _, _ = select_context(tmp_path, managed=True, pinned=True)
    assert result.returncode == 0, result.stderr
    assert (checkout.parent / ".ssh/known_hosts").read_text() == "192.0.2.10 ssh-ed25519 fixture-public-key\n"


def test_cli_context_keeps_its_existing_guest_pin_reset(tmp_path):
    result, checkout, _, _ = select_context(tmp_path, pinned=True)
    assert result.returncode == 0, result.stderr
    assert (checkout.parent / ".ssh/known_hosts").read_text() == ""


def test_default_context_still_selects_its_existing_secret_links(tmp_path):
    result, checkout, workspace, _ = select_context(tmp_path)
    assert result.returncode == 0, result.stderr
    for relative in ("range42-ansible_roles-debug-devkit/secrets", "range42-playbooks/scenarios/demo/secrets"):
        assert (checkout / relative).resolve() == workspace / "secrets"
