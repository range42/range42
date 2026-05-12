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


# ── detection functions ──────────────────────────────────────────────────────

def check_command(cmd):
    """Check if a command is available in PATH."""
    return shutil.which(cmd) is not None


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

    # ssh-agent running check
    agent_running = check_ssh_agent_running()
    results.append({
        "badge": "PASS" if agent_running else "WARN",
        "label": "ssh-agent (running)",
        "detail": "" if agent_running else "  not running — will be handled during deployment",
        "required": False,
    })

    return results, fail


def get_apt_install_command(results):
    """
    Build a single 'sudo apt-get install ...' command from failed/warned checks.
    Only includes checks that have an apt fix (not manual).
    Returns None if nothing to install.
    """
    packages = set()
    for r in results:
        apt_fix = r.get("apt_fix")
        if apt_fix and r["badge"] in ("FAIL", "WARN"):
            # extract package name from "sudo apt install <pkg>"
            pkg = apt_fix.replace("sudo apt install ", "").strip()
            packages.add(pkg)
    if not packages:
        return None
    return "sudo apt-get update && sudo apt-get install -y " + " ".join(sorted(packages))


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
