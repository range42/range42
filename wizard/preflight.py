"""
wizard/preflight.py — preflight check definitions and detection logic

Pure stdlib — no textual dependency. Used by range42-init.py before TUI starts.
"""

import os
import shutil
import subprocess
from pathlib import Path

# ── check definitions ────────────────────────────────────────────────────────

CHECKS = [
    # sudo is not installed by default on Debian minimal — required for deployment
    # manual=True means the wizard cannot auto-install this, user must do it themselves
    {"label": "sudo",             "cmd": "sudo",             "fix": "as root: apt-get install sudo, add your user to sudo group, then re-login", "required": True, "manual": True},
    {"label": "ansible",          "cmd": "ansible",          "fix": "sudo apt install ansible",        "required": True,  "manual": False},
    {"label": "ansible-playbook", "cmd": "ansible-playbook", "fix": None,                              "required": True,  "manual": False},
    {"label": "ansible-vault",    "cmd": "ansible-vault",    "fix": None,                              "required": True,  "manual": False},
    {"label": "ssh-keygen",       "cmd": "ssh-keygen",       "fix": "sudo apt install openssh-client", "required": True,  "manual": False},
    {"label": "ssh-agent",        "cmd": "ssh-agent",        "fix": "sudo apt install openssh-client", "required": True,  "manual": False},
    {"label": "ssh-copy-id",      "cmd": "ssh-copy-id",      "fix": "sudo apt install openssh-client", "required": True,  "manual": False},
    {"label": "sshpass",          "cmd": "sshpass",          "fix": "sudo apt install sshpass",        "required": True,  "manual": False},
    {"label": "git",              "cmd": "git",              "fix": "sudo apt install git",            "required": True,  "manual": False},
    {"label": "pip3",             "cmd": "pip3",             "fix": "sudo apt install python3-pip",    "required": True,  "manual": False},
    {"label": "keychain",         "cmd": "keychain",         "fix": "sudo apt install keychain",       "required": False, "manual": False},
    {"label": "zsh",              "cmd": "zsh",              "fix": "sudo apt install zsh",            "required": False, "manual": False},
]

COLLECTIONS = [
    "community.crypto",
    "community.general",
]

# Python modules required by Ansible modules invoked from playbook 01.
# community.crypto.openssh_keypair needs bcrypt to create passphrase-protected
# ed25519 keys (the cryptography library uses bcrypt for the AES key derivation
# when encrypting the private key file). Without bcrypt installed, the wizard
# fails at the GENERATE PROXMOX ROOT SSH KEY task with :
#     cryptography.exceptions.UnsupportedAlgorithm: Need bcrypt module
PYTHON_DEPS = [
    {"label": "python3-bcrypt", "module": "bcrypt", "fix": "sudo apt install python3-bcrypt", "required": True, "manual": False},
]

# Key name handed to `keychain --eval` for the sole purpose of forcing an
# ssh-agent to start. It MUST NOT match any real key: keychain then loads
# nothing and never asks for a passphrase. See ensure_ssh_agent_running().
_AGENT_BOOTSTRAP_KEY = "r42_force_agent_start__not_a_real_key"


# ── detection functions ──────────────────────────────────────────────────────

def check_command(cmd):
    """Check if a command is available in PATH."""
    return shutil.which(cmd) is not None


def check_python_module(name):
    """Check if a Python module is importable from the current python3."""
    r = subprocess.run(
        ["python3", "-c", f"import {name}"],
        capture_output=True,
    )
    return r.returncode == 0


def get_version(cmd):
    """Get version string for known commands."""
    if cmd == "ansible":
        r = subprocess.run(["ansible", "--version"], capture_output=True, text=True)
        return r.stdout.splitlines()[0] if r.returncode == 0 and r.stdout else ""
    if cmd == "git":
        r = subprocess.run(["git", "--version"], capture_output=True, text=True)
        return r.stdout.strip().split()[-1] if r.returncode == 0 and r.stdout else ""
    return ""


def check_collection(name):
    """Check if an Ansible collection is installed."""
    if not shutil.which("ansible-galaxy"):
        return False
    r = subprocess.run(
        ["ansible-galaxy", "collection", "list"],
        capture_output=True, text=True,
    )
    return any(line.strip().startswith(name) for line in r.stdout.splitlines())


def check_ssh_agent_running():
    """Check if ssh-agent is running and the socket is valid."""
    if not shutil.which("ssh-add"):
        return False
    sock = os.environ.get("SSH_AUTH_SOCK", "")
    if not sock or not os.path.exists(sock):
        return False
    r = subprocess.run(["ssh-add", "-l"], capture_output=True)
    return r.returncode != 2  # 2 = agent not running


def ensure_ssh_agent_running():
    """
    Make sure an ssh-agent is reachable, starting one if there is none.

    Returns (ok, started) — started is True only when this call spawned the agent.

    NO KEY IS ADDED HERE. No passphrase is ever requested by this function: it
    starts an empty agent and nothing else. Loading the range42 keys stays the
    job of the playbooks (roles/proxmox.init/tasks/00_load_root_ssh_key.yml).

    Why it has to happen during preflight, before the checks are done:
    playbook 02 reaches Proxmox through the native ssh connection plugin, and
    the local ssh client it spawns reads SSH_AUTH_SOCK from the environment that
    ansible-playbook inherited. A play-level `environment:` cannot reach that
    client, so the socket has to exist in the wizard's own environment.
    post_wizard() hands os.environ.copy() to ansible-playbook, so exporting the
    socket here is what carries the agent all the way down.

    On a fresh VM nothing else can do it: the only agent starter in the project
    is `keychain` in the deployed .zshrc, and both keychain (01_packages.yml)
    and that .zshrc (04_dot_files.yml) are installed by playbook 03 — after the
    playbook that needs the agent. Hence this bootstrap step.

    The agent outlives the wizard on purpose: post_wizard() needs it.
    """
    if check_ssh_agent_running():
        return True, False
    if not shutil.which("keychain"):
        return False, False
    try:
        # keychain is preferred over a bare `ssh-agent -s`: it re-attaches to an
        # agent already recorded in ~/.keychain/<host>-sh instead of spawning a
        # new one at every wizard run, and it is already the project's idiom
        # (see roles/deployer.bootstrap/files/dot_files/zshrc).
        #
        # The key name is DELIBERATELY one that cannot exist. keychain then
        # starts/re-attaches the agent, loads NOTHING, warns
        # "can't find <name>; skipping" on stderr and still exits 0 with the
        # shell assignments on stdout. Passing a REAL key name here would make
        # keychain prompt for its passphrase during preflight, which is exactly
        # what must not happen. Do not "fix" this to id_rsa.
        r = subprocess.run(
            ["keychain", "--eval", _AGENT_BOOTSTRAP_KEY],
            capture_output=True, text=True, timeout=15,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return False, False
    if not r.stdout:
        return False, False
    # stdout carries shell assignments, same shape as `ssh-agent -s`:
    #   SSH_AUTH_SOCK=/tmp/ssh-XXXX/agent.123; export SSH_AUTH_SOCK;
    #   SSH_AGENT_PID=124; export SSH_AGENT_PID;
    for line in r.stdout.splitlines():
        for var in ("SSH_AUTH_SOCK", "SSH_AGENT_PID"):
            if line.startswith(var + "="):
                os.environ[var] = line.split("=", 1)[1].split(";", 1)[0].strip()
    return check_ssh_agent_running(), True


# ── run all checks ───────────────────────────────────────────────────────────

def run_all_checks(example_dir):
    """
    Run all preflight checks and return structured results.

    Returns:
        list[dict]: each dict has keys:
            - badge: "PASS" | "WARN" | "FAIL"
            - label: display name
            - detail: version string or fix command
            - required: bool
        bool: True if any required check failed
    """
    results = []
    fail = False

    # check sudo first — if missing, stop here (nothing else can be installed)
    if not check_command("sudo"):
        sudo_check = [c for c in CHECKS if c["cmd"] == "sudo"][0]
        results.append({
            "badge": "FAIL",
            "label": sudo_check["label"],
            "detail": f"  {sudo_check['fix']}  [manual]",
            "required": True,
            "apt_fix": None,
        })
        return results, True

    # command checks
    for check in CHECKS:
        ok = check_command(check["cmd"])
        ver = get_version(check["cmd"]) if ok else ""

        if ok:
            badge = "PASS"
            detail = f"  {ver}" if ver else ""
        elif check["required"]:
            badge = "FAIL"
            if check.get("manual") and check["fix"]:
                detail = f"  {check['fix']}  [manual]"
            elif check["fix"]:
                detail = f"  {check['fix']}  [Install & retry]"
            else:
                detail = ""
            fail = True
        else:
            badge = "WARN"
            if check["fix"]:
                detail = f"  {check['fix']}  [Install & retry]"
            else:
                detail = ""

        results.append({
            "badge": badge,
            "label": check["label"],
            "detail": detail,
            "required": check["required"],
            "apt_fix": check["fix"] if not ok and not check.get("manual") and (check.get("fix") or "").startswith("sudo apt") else None,
        })

    # python module checks (e.g., bcrypt for openssh_keypair with passphrase)
    for dep in PYTHON_DEPS:
        ok = check_python_module(dep["module"])

        if ok:
            badge = "PASS"
            detail = ""
        elif dep["required"]:
            badge = "FAIL"
            detail = f"  {dep['fix']}  [Install & retry]"
            fail = True
        else:
            badge = "WARN"
            detail = f"  {dep['fix']}  [Install & retry]"

        results.append({
            "badge": badge,
            "label": dep["label"],
            "detail": detail,
            "required": dep["required"],
            "apt_fix": dep["fix"] if not ok and (dep.get("fix") or "").startswith("sudo apt") else None,
        })

    # collection checks
    for name in COLLECTIONS:
        ok = check_collection(name)
        results.append({
            "badge": "PASS" if ok else "WARN",
            "label": f"collection {name}",
            "detail": "" if ok else f"  fix: ansible-galaxy collection install {name}",
            "required": False,
        })

    # example inventory check
    ok = example_dir.exists()
    if not ok:
        fail = True
    results.append({
        "badge": "PASS" if ok else "FAIL",
        "label": "example inventory",
        "detail": "" if ok else f"  path: {example_dir}",
        "required": True,
    })

    # range42-playbooks repo check (auto-clone if missing)
    # script_dir = range42/ repo root — from example_dir (inventories/example) go up 2 levels
    script_dir = Path(example_dir).parent.parent
    badge, detail = ensure_playbooks_repo(script_dir)
    if badge == "FAIL":
        fail = True
    results.append({
        "badge": badge,
        "label": "range42-playbooks",
        "detail": detail,
        "required": True,
    })

    # ssh-agent — STARTED here when absent, not merely reported.
    # Playbook 02 needs a reachable agent and nothing earlier in the run can
    # provide one on a fresh VM. See ensure_ssh_agent_running() for why the
    # socket must land in this process' environment. No key is loaded here.
    agent_running, agent_started = ensure_ssh_agent_running()
    if agent_running:
        detail = "  started by the wizard" if agent_started else ""
    elif not shutil.which("keychain"):
        detail = "  keychain missing — install it above, the agent starts on the next pass"
    else:
        detail = "  could not start one — playbook 02 will fail on passphrase-protected keys"
    results.append({
        "badge": "PASS" if agent_running else "WARN",
        "label": "ssh-agent (running)",
        "detail": detail,
        "required": False,
    })

    return results, fail


def get_apt_install_packages(results) -> list:
    """
    Return a sorted list of package names that need to be installed.
    Only includes checks that have an apt fix (not manual) and are FAIL or WARN.
    Returns an empty list if nothing to install.
    """
    packages = set()
    for r in results:
        apt_fix = r.get("apt_fix")
        if apt_fix and r["badge"] in ("FAIL", "WARN"):
            # extract package name from "sudo apt install <pkg>"
            pkg = apt_fix.replace("sudo apt install ", "").strip()
            packages.add(pkg)
    return sorted(packages)


def get_apt_install_command(results):
    """
    Build a single 'sudo apt-get install ...' command from failed/warned checks.
    Only includes checks that have an apt fix (not manual).
    Returns None if nothing to install (used for display / button visibility).
    """
    packages = get_apt_install_packages(results)
    if not packages:
        return None
    return "sudo apt-get update && sudo apt-get install -y " + " ".join(packages)


# files required in each scenario's templates/ dir for it to be deployable
SCENARIO_REQUIRED_FILES = (
    "ansible-inventory.j2",
    "ansible-vars.yml",
    "ssh-config.j2",
    "vault-example.yml",
)


def _has_deployable_scenario(scenarios_dir):
    """Return True if scenarios_dir contains at least one scenario with a complete templates/ dir."""
    if not scenarios_dir.exists():
        return False
    for d in scenarios_dir.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        tmpl = d / "templates"
        if tmpl.is_dir() and all((tmpl / f).exists() for f in SCENARIO_REQUIRED_FILES):
            return True
    return False


def ensure_playbooks_repo(script_dir):
    """
    Ensure range42-playbooks is cloned as a sibling of the range42 repo AND
    that at least one scenario is deployable (has a complete templates/ dir).

    After the scenario-templates migration refactor, scenario templates + group_vars
    live in range42-playbooks. The wizard (and the Ansible roles) need a local
    clone on the operator to find them (the template module reads src on the
    controller, not on the target).

    Behavior:
      - if sibling dir exists with at least 1 deployable scenario → PASS
      - if sibling dir exists but no deployable scenario → FAIL (outdated clone)
      - if sibling dir is missing → attempt silent git clone → PASS if clone OK
      - any failure (no network, git missing, clone timeout, etc.) → FAIL

    Returns: (badge, detail)
    """
    playbooks_dir = Path(script_dir).parent / "range42-playbooks"
    scenarios_dir = playbooks_dir / "scenarios"

    # Case 1: dir exists and has at least one deployable scenario
    if playbooks_dir.exists() and _has_deployable_scenario(scenarios_dir):
        return "PASS", f"  {playbooks_dir}"

    # Case 2: dir exists but is outdated (no deployable scenario)
    # can't auto-update (would need git pull, risky for user local changes)
    if playbooks_dir.exists():
        return "FAIL", (
            f"  {playbooks_dir} exists but has no deployable scenario "
            f"(missing templates/ in scenarios/*/). "
            f"Update with: cd {playbooks_dir} && git pull"
        )

    # Case 3: dir missing → try clone
    try:
        subprocess.run(
            ["git", "clone", "--quiet",
             "https://github.com/range42/range42-playbooks.git",
             str(playbooks_dir)],
            check=True, capture_output=True, text=True, timeout=60,
        )
        # verify the clone yielded at least one deployable scenario
        if not _has_deployable_scenario(scenarios_dir):
            return "FAIL", f"  cloned but no deployable scenario found in {scenarios_dir}"
        return "PASS", f"  cloned → {playbooks_dir}"
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip().splitlines()[-1] if e.stderr else "unknown error"
        return "FAIL", f"  clone failed: {err}"
    except subprocess.TimeoutExpired:
        return "FAIL", "  clone timed out (check network)"
    except FileNotFoundError:
        return "FAIL", "  git not found (install git first)"
