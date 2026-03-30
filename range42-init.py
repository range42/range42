#!/usr/bin/env python3
"""
range42-init.py  —  interactive infrastructure setup  (Textual edition)

  Install : pip install textual
  Run     : python3 range42-init.py
"""

import os, re, shutil, subprocess, ssl, sys, urllib.request

# force truecolor — SSH doesn't forward COLORTERM, causing Textual
# to fall back to 16-color ANSI palette (ugly DOS blue)
os.environ.setdefault("COLORTERM", "truecolor")
from pathlib import Path

# check textual dependency before importing
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.reactive import reactive
    from textual.theme import Theme
    from textual.widget import Widget
    from textual.widgets import (
        Button, DataTable, Footer, Header,
        Input, Label, LoadingIndicator, RichLog, Static, Rule,
    )

    # themes — hex-only, independent of terminal palette
    R42_THEMES = [
        Theme(name="r42-solarized", dark=True,
              primary="#268bd2", secondary="#2aa198", accent="#b58900",
              warning="#cb4b16", error="#dc322f", success="#859900",
              foreground="#839496", background="#002b36",
              surface="#073642", panel="#073642", boost="#0d4a5a"),
        Theme(name="r42-catppuccin", dark=True,
              primary="#89b4fa", secondary="#94e2d5", accent="#f9e2af",
              warning="#fab387", error="#f38ba8", success="#a6e3a1",
              foreground="#cdd6f4", background="#1e1e2e",
              surface="#313244", panel="#45475a", boost="#585b70"),
        Theme(name="r42-midnight", dark=True,
              primary="#38bdf8", secondary="#2dd4bf", accent="#fbbf24",
              warning="#fb923c", error="#f87171", success="#4ade80",
              foreground="#94a3b8", background="#0f172a",
              surface="#1e293b", panel="#334155", boost="#475569"),
    ]
except ImportError:
    # try auto-install in a local venv
    _venv = Path(__file__).parent / ".venv-wizard"
    _pip = _venv / "bin" / "pip"
    _python = _venv / "bin" / "python3"

    if not _venv.exists():
        print()
        print("  \033[1;33mINFO\033[0m  textual library not found — creating local venv...")
        print()
        import venv
        venv.create(str(_venv), with_pip=True)
        subprocess.run([str(_pip), "install", "--quiet", "textual"], check=False)

    if _python.exists():
        # re-exec with the venv python
        os.execv(str(_python), [str(_python), __file__] + sys.argv[1:])
    else:
        print()
        print("  \033[1;31mERROR\033[0m  failed to create venv for textual.")
        print()
        print("  Manual install:")
        print("    \033[36mpython3 -m venv .venv-wizard && .venv-wizard/bin/pip install textual\033[0m")
        print("    \033[36m.venv-wizard/bin/python3 range42-init.py\033[0m")
        sys.exit(1)
    print()
    sys.exit(1)
from textual import work, on
from rich.text import Text

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent.resolve()
INVENTORIES = SCRIPT_DIR / "inventories"
EXAMPLE_DIR = INVENTORIES / "example"

# ── state ──────────────────────────────────────────────────────────────────────
class _S:
    codename        = ""
    proxmox_address = ""
    proxmox_node    = "pve"
    scenario        = "demo_lab"
    deployer_user   = os.environ.get("USER", "")
    deployer_ip     = "127.0.0.1"
    network_iface   = "enp3s0"
    proxmox_root_pw = ""
    sudo_pw         = ""
    deployer_cli_pw = ""
    setup_mode      = "new"
    preflight_ok    = False
    deploy_now      = False
S = _S()

# ── helpers ────────────────────────────────────────────────────────────────────
def cmd_ok(c): return bool(shutil.which(c))

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def col_ok(n):
    _, o, _ = run("ansible-galaxy", "collection", "list")
    return n in o

def existing():
    if not INVENTORIES.exists(): return []
    return [d.name for d in sorted(INVENTORIES.iterdir())
            if d.is_dir() and d.name != "example" and (d / "hosts.yml").exists()]

def prefill(name):
    vf = INVENTORIES / name / "group_vars" / "all" / "vars.yml"
    if not vf.exists(): return
    txt = vf.read_text()
    def ex(k):
        m = re.search(rf'^{k}:\s*"([^"]*)"', txt, re.M)
        return m.group(1) if m else ""
    S.codename        = name
    S.proxmox_address = ex("INFRASTRUCTURE_PROXMOX_ADDRESS")
    S.proxmox_node    = ex("proxmox_node") or "pve"
    S.deployer_user   = ex("DEPLOYER_CLI_USER") or S.deployer_user
    S.deployer_ip     = ex("deployer_cli_ip") or "127.0.0.1"
    S.network_iface   = ex("infrastructure_proxmox_default_network_card_interface") or "enp3s0"
    for d in (INVENTORIES / name / "group_vars").iterdir():
        if d.name != "all": S.scenario = d.name; break

def sed_f(path, old, new):
    p = Path(path)
    if not p.exists():
        print(f"  WARNING: sed_f — file not found: {p}")
        return False
    content = p.read_text()
    if old not in content:
        print(f"  WARNING: sed_f — pattern not found in {p.name}: {old[:60]}")
        return False
    p.write_text(content.replace(old, new))
    return True

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
/* Uses $variables from RANGE42_THEME — independent of terminal palette */

Screen  { background: $background; color: $foreground; }

Header  {
    background: $surface; color: $primary; text-style: bold;
    border-bottom: tall $panel;
}
Footer  { background: $surface; color: $panel; border-top: tall $panel; }

#main   { layout: horizontal; height: 1fr; }

#sidebar {
    width: 42; background: $surface; padding: 2 2;
    border-right: tall $panel; height: 1fr;
}

#content-wrap { width: 1fr; height: 1fr; layout: vertical; }
#content      { padding: 2 4; height: 1fr; overflow-y: auto; }

#btn-row {
    dock: bottom; height: 5; layout: horizontal; align: center middle;
    padding: 0 3; background: $surface; border-top: tall $panel;
}

Button          { background: $surface; border: round $panel; color: $primary; margin: 0 1; min-width: 16; }
Button:hover    { border: tall $primary; }
Button.-ok      { border: round $success; color: $success; }
Button.-ok:hover { border: tall $success; }
Button.-danger  { border: round $error; color: $error; }
Button:disabled { opacity: 0.35; }
Button:focus    { border: tall $primary; }

.title  { color: $primary; text-style: bold; margin-bottom: 1; }
.hint   { color: $panel; margin-bottom: 1; }
.err    { color: $error; }
.muted  { color: $foreground; }
Rule    { color: $panel; margin: 1 0; }

.field        { margin-bottom: 3; }
Input         { background: $surface; border: tall $panel; color: $foreground; }
Input:focus   { border: tall $primary; }

.pf-badge-pass  { color: $success; width: 7; text-style: bold; }
.pf-badge-warn  { color: $accent; width: 7; text-style: bold; }
.pf-badge-fail  { color: $error; width: 7; text-style: bold; }
.pf-badge-info  { color: $primary; width: 7; text-style: bold; }
.pf-row         { height: 1; }
.pf-msg         { color: $foreground; width: 1fr; }
.pf-kv          { color: $success; }

DataTable       { background: $surface; border: tall $panel; height: auto; max-height: 22; margin-bottom: 1; }
DataTable > .datatable--header { background: $background; color: $primary; }
DataTable > .datatable--cursor { background: $boost; }

RichLog         { background: $background; border: tall $panel; height: 1fr; min-height: 14; }
LoadingIndicator { color: $primary; }

#choice-list Button { margin-bottom: 1; width: 100%; }
#overwrite-confirm  { height: auto; margin-bottom: 1; align: center middle; content-align: center middle; }
.warn               { color: $accent; }
"""

# ── sidebar (table of contents) ────────────────────────────────────────────────
STEPS = [
    (0, "prerequisites"),
    (1, "welcome"),
    (2, "codename"),
    (2, "proxmox address"),
    (2, "proxmox node"),
    (2, "connectivity"),
    (3, "scenario"),
    (3, "deployer IP"),
    (3, "deployer user"),
    (3, "network"),
    (4, "root password"),
    (4, "sudo password"),
    (5, "review"),
    (6, "deploy"),
]

class Sidebar(Static):
    step: reactive[int] = reactive(0)

    def render(self) -> Text:
        t = Text()
        t.append("  wizard steps\n\n", style="#268bd2 bold")
        seen: set[int] = set()
        for num, name in STEPS:
            sub   = num in seen
            seen.add(num)
            if num < self.step:
                dot, ds, ns = "✓", "bold #859900", "#859900"
            elif num == self.step:
                dot, ds, ns = "●", "bold #268bd2", "bold #93a1a1"
            else:
                dot, ds, ns = "○", "#586e75", "#586e75"
            if sub:
                t.append(f"      {name}\n", style=ns)
            else:
                t.append(f"  {dot} ", style=ds)
                t.append(f"{name}\n",   style=ns)
        t.append("\n\n")
        t.append("  press t to change theme", style="#586e75")
        return t


# ── base step widget ───────────────────────────────────────────────────────────
class Step(Widget):
    STEP_NUM   = 0
    NEXT_LABEL = "Continue →"
    NEXT_CLASS = "-ok"
    SHOW_BACK  = True

    def handle_next(self, app: "Range42"): pass
    def handle_back(self, app: "Range42"): pass


# ── step 0 — preflight ────────────────────────────────────────────────────────
class StepPreflight(Step):
    STEP_NUM  = 0
    SHOW_BACK = False

    def compose(self) -> ComposeResult:
        yield Label("◆  prerequisites checks", classes="title")
        yield Rule()
        yield Container(id="pf-rows")
        yield LoadingIndicator(id="pf-spin")

    def on_mount(self):
        self.app.query_one("#btn-next", Button).disabled = True
        self.check()

    @work(thread=True)
    def check(self):
        import time
        checks = [
            ("ansible",          "ansible",          "sudo apt install ansible",        True),
            ("ansible-playbook", "ansible-playbook", None,                              True),
            ("ansible-vault",    "ansible-vault",    None,                              True),
            ("ssh-keygen",       "ssh-keygen",       "sudo apt install openssh-client", True),
            ("sshpass",          "sshpass",          "sudo apt install sshpass",        False),
            ("git",              "git",              "sudo apt install git",            True),
        ]
        fail = False
        for label, cmd, fix, required in checks:
            ok  = cmd_ok(cmd)
            ver = ""
            if ok and cmd == "ansible":
                _, o, _ = run("ansible", "--version"); ver = o.splitlines()[0] if o else ""
            elif ok and cmd == "git":
                _, o, _ = run("git", "--version"); ver = o.strip().split()[-1] if o else ""
            if ok:
                badge, kv = "PASS", f"  {ver}" if ver else ""
            elif required:
                badge, kv = "FAIL", f"  fix: {fix}" if fix else ""; fail = True
            else:
                badge, kv = "WARN", f"  fix: {fix}" if fix else ""
            self.app.call_from_thread(self._row, badge, label, kv)
            time.sleep(0.12)

        for name in ("community.crypto", "community.general"):
            ok    = col_ok(name)
            badge = "PASS" if ok else "WARN"
            kv    = f"  fix: ansible-galaxy collection install {name}" if not ok else ""
            self.app.call_from_thread(self._row, badge, f"collection {name}", kv)
            time.sleep(0.12)

        ok = EXAMPLE_DIR.exists()
        self.app.call_from_thread(
            self._row, "PASS" if ok else "FAIL", "example inventory",
            "" if ok else f"  path: {EXAMPLE_DIR}")
        if not ok: fail = True

        S.preflight_ok = not fail
        self.app.call_from_thread(self._done, fail)

    def _add_row(self, badge, msg, kv=""):
        cls = {"PASS":"pf-badge-pass","WARN":"pf-badge-warn",
               "FAIL":"pf-badge-fail","INFO":"pf-badge-info"}[badge]
        row = Horizontal(classes="pf-row")
        row.compose_add_child(Label(badge, classes=cls))
        row.compose_add_child(Label(msg,   classes="pf-msg"))
        row.compose_add_child(Label(kv,    classes="pf-kv"))
        self.query_one("#pf-rows").mount(row)

    def _row(self, badge, msg, kv=""):
        cls = {"PASS":"pf-badge-pass","WARN":"pf-badge-warn",
               "FAIL":"pf-badge-fail","INFO":"pf-badge-info"}[badge]
        row = Horizontal(classes="pf-row")
        row.compose_add_child(Label(badge, classes=cls))
        row.compose_add_child(Label(msg,   classes="pf-msg"))
        row.compose_add_child(Label(kv,    classes="pf-kv"))
        self.query_one("#pf-rows").mount(row)

    def _done(self, fail):
        self.query_one("#pf-spin").remove()
        self.query_one("#pf-rows").mount(Rule())
        self._row("FAIL" if fail else "PASS",
                  "fix above and re-run" if fail else "all checks passed")
        # clear passwords from state after use
        S.proxmox_root_pw = S.sudo_pw = S.deployer_cli_pw = ""

        btn = self.app.query_one("#btn-next", Button)
        btn.disabled = False
        if fail:
            btn.label = "Exit"
            btn.remove_class("-ok"); btn.add_class("-danger")

    def handle_next(self, app):
        if not S.preflight_ok: app.exit(); return
        app._go(StepExisting() if existing() else StepWelcome())


# ── step 0b — existing configs ────────────────────────────────────────────────
class StepExisting(Step):
    STEP_NUM   = 0
    SHOW_BACK  = False
    NEXT_LABEL = ""   # buttons handled manually

    def compose(self) -> ComposeResult:
        yield Label("◆  existing configurations detected", classes="title")
        yield Rule()
        yield Static(
            "  One or more inventories already exist.\n"
            "  Choose to create a new setup or overwrite an existing one.",
            classes="muted")
        yield Static("")
        yield Container(id="choice-list")

    def on_mount(self):
        self.app.query_one("#btn-next", Button).display = False
        self.app.query_one("#btn-back", Button).display = False
        lst = self.query_one("#choice-list")
        lst.mount(Button(
            "  ◆  new  —  create a new infrastructure setup",
            id="c-new", classes="-ok"))
        for cfg in existing():
            lst.mount(Button(
                f"  ↺  {cfg}  —  overwrite existing configuration",
                id=f"c-{cfg}"))

    @on(Button.Pressed)
    def pick(self, e: Button.Pressed):
        bid = e.button.id or ""
        if not bid.startswith("c-"): return
        mode = bid[2:]
        S.setup_mode = mode
        if mode != "new": prefill(mode)
        self.app._go(StepWelcome())


# ── step 1 — welcome ──────────────────────────────────────────────────────────
class StepWelcome(Step):
    STEP_NUM = 1

    def compose(self) -> ComposeResult:
        if S.setup_mode == "new":
            yield Label("◆  range42  —  setup wizard", classes="title")
            yield Rule()
            yield Static("""\
  Welcome to the range42 infrastructure setup.

  This wizard will guide you through the initial
  configuration of your cyber range lab.

  It will:
    1. Ask you a few questions about your Proxmox server
    2. Create an Ansible inventory with your settings
    3. Show you the exact commands to run next

  You will need:
    - Your Proxmox server address (IP or FQDN)
    - The Proxmox node name (visible in the Proxmox web UI)""", classes="muted")
        else:
            yield Label(f"◆  range42  —  reconfigure {S.setup_mode}", classes="title")
            yield Rule()
            yield Static(f"""\
  Reconfiguring existing setup: {S.setup_mode}

  The wizard will show the current values as defaults.
  Press Enter to keep a value, or type a new one.

  The existing inventory will be overwritten.""", classes="muted")

    def handle_next(self, app): app._go(StepCodename())
    def handle_back(self, app):
        app._go(StepExisting() if existing() else StepPreflight())


# ── step 2 — infrastructure ───────────────────────────────────────────────────
class StepCodename(Step):
    STEP_NUM = 2

    def compose(self) -> ComposeResult:
        yield Label("◆  step 1/3  —  infrastructure codename", classes="title")
        yield Rule()
        yield Static(
            "  A short name that identifies your Proxmox server.\n"
            "  Used everywhere in range42: directories, SSH config, key names.\n\n"
            "  Letters, numbers, hyphens, underscores, dots. No spaces.\n"
            "  Examples: hv-lab-01, proxmox_home, my.server",
            classes="muted")
        yield Static("")
        yield Input(value=S.codename, placeholder="hv-lab-01", id="i-cn")
        yield Label("", id="e-cn", classes="err")

    def handle_next(self, app):
        cn = self.query_one("#i-cn", Input).value.strip()
        if not cn:
            self.query_one("#e-cn", Label).update("✗ codename is required"); return
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', cn):
            self.query_one("#e-cn", Label).update(
                "✗ letters, numbers, hyphens, underscores, dots only"); return
        self.query_one("#e-cn", Label).update("")
        S.codename = cn
        app._go(StepAddress())

    def handle_back(self, app): app._go(StepWelcome())


class StepAddress(Step):
    STEP_NUM = 2

    def compose(self) -> ComposeResult:
        yield Label("◆  step 1/3  —  proxmox address", classes="title")
        yield Rule()
        yield Static(
            "  IP address or FQDN of your Proxmox server.\n"
            "  Do NOT include the port (:8006) — it will be added automatically.\n\n"
            "  Examples: 192.168.1.100 · proxmox.local · my-server.tailnet.ts.net",
            classes="muted")
        yield Static("")
        yield Input(value=S.proxmox_address, placeholder="192.168.1.100", id="i-addr")
        yield Label("", id="e-addr", classes="err")

    def handle_next(self, app):
        addr = self.query_one("#i-addr", Input).value.strip()
        if not addr:
            self.query_one("#e-addr", Label).update("✗ address is required"); return
        self.query_one("#e-addr", Label).update("")
        S.proxmox_address = addr.split(":")[0]
        app._go(StepNode())

    def handle_back(self, app): app._go(StepCodename())


class StepNode(Step):
    STEP_NUM = 2

    def compose(self) -> ComposeResult:
        yield Label("◆  step 1/3  —  proxmox node name", classes="title")
        yield Rule()
        yield Static(
            "  The exact node name as shown in your Proxmox web UI.\n"
            "  Look in the top-left corner, under 'Datacenter'.\n\n"
            "  Examples: pve, proxmox, node1",
            classes="muted")
        yield Static("")
        yield Input(value=S.proxmox_node, placeholder="pve", id="i-node")

    def handle_next(self, app):
        node = self.query_one("#i-node", Input).value.strip()
        S.proxmox_node = node or "pve"
        app._go(StepProxmoxCheck())

    def handle_back(self, app): app._go(StepAddress())


# ── step 2b — proxmox connectivity check ──────────────────────────────────────
class StepProxmoxCheck(Step):
    STEP_NUM  = 2
    SHOW_BACK = False   # hidden until check completes

    def compose(self) -> ComposeResult:
        yield Label("◆  testing proxmox connection", classes="title")
        yield Rule()
        yield Label(f"  connecting to {S.proxmox_address}:8006 ...", classes="muted")
        yield LoadingIndicator(id="spin")
        yield Label("", id="result")

    def on_mount(self):
        self.app.query_one("#btn-next", Button).disabled = True
        self.do_check()

    @work(thread=True)
    def do_check(self):
        import time; time.sleep(0.4)
        ok = False
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            urllib.request.urlopen(
                f"https://{S.proxmox_address}:8006/api2/json", timeout=5, context=ctx)
            ok = True
        except urllib.error.HTTPError:
            # 401/403 = proxmox is responding, just no auth — that's fine
            ok = True
        except Exception:
            pass
        self.app.call_from_thread(self._show, ok)

    def _show(self, ok):
        self.query_one("#spin").display = False
        r = self.query_one("#result", Label)
        if ok:
            r.update(f"\n  [bold #4ade80]✓[/bold #4ade80]  proxmox reachable at {S.proxmox_address}:8006")
        else:
            r.update(
                f"\n  [bold #fbbf24]![/bold #fbbf24]  could not reach {S.proxmox_address}:8006\n\n"
                "  This is NOT a blocker — the address will be saved.\n"
                "  Check: server on? firewall? VPN connected?")
        self.app.query_one("#btn-next", Button).disabled = False
        # always show Back after check so user can fix address if needed
        btn_back = self.app.query_one("#btn-back", Button)
        btn_back.display  = True
        btn_back.disabled = False

    def handle_next(self, app): app._go(StepScenario())
    def handle_back(self, app): app._go(StepNode())


# ── step 3 — scenario, deployer, network (split) ─────────────────────────────

class StepScenario(Step):
    STEP_NUM = 3

    def compose(self) -> ComposeResult:
        yield Label("◆  step 2/3  —  scenario", classes="title")
        yield Rule()
        yield Static(
            "  Which lab scenario to deploy on this infrastructure.\n\n"
            "  demo_lab is the standard cyber range with admin VMs,\n"
            "  student boxes, and vulnerable targets.\n\n"
            "  If you're unsure, keep the default.",
            classes="muted")
        yield Static("")
        yield Input(value=S.scenario, placeholder="demo_lab", id="i-scenario")

    def handle_next(self, app):
        S.scenario = self.query_one("#i-scenario", Input).value.strip() or "demo_lab"
        app._go(StepDeployerUser())

    def handle_back(self, app): app._go(StepProxmoxCheck())


class StepDeployerIP(Step):
    STEP_NUM = 3

    def compose(self) -> ComposeResult:
        yield Label("◆  step 2/3  —  deployer-cli IP", classes="title")
        yield Rule()
        yield Static(
            "  IP of the machine running Ansible (the deployer-cli).\n\n"
            "  127.0.0.1 = this machine (localhost).\n"
            "  Change only if Ansible runs on a remote VM.",
            classes="muted")
        yield Static("")
        yield Input(value=S.deployer_ip, placeholder="127.0.0.1", id="i-dip")

    def handle_next(self, app):
        S.deployer_ip = self.query_one("#i-dip", Input).value.strip() or "127.0.0.1"
        app._go(StepDeployerUser())

    def handle_back(self, app): app._go(StepScenario())


class StepDeployerUser(Step):
    STEP_NUM = 3

    def compose(self) -> ComposeResult:
        yield Label("◆  step 2/3  —  deployer-cli user", classes="title")
        yield Rule()
        yield Static(
            "  Linux username on the deployer machine.\n"
            "  This is YOUR user, on the machine running Ansible.",
            classes="muted")
        yield Static("")
        yield Input(value=S.deployer_user, placeholder="alice", id="i-duser")

    def handle_next(self, app):
        S.deployer_user = self.query_one("#i-duser", Input).value.strip() or os.environ.get("USER", "")
        app._go(StepNetwork())

    def handle_back(self, app): app._go(StepDeployerIP())


class StepNetwork(Step):
    STEP_NUM = 3

    def compose(self) -> ComposeResult:
        yield Label("◆  step 2/3  —  network interface", classes="title")
        yield Rule()
        yield Static(
            "  Physical network interface on the Proxmox server.\n"
            "  Used for VM networking (NAT bridges).\n\n"
            "  Check with: ip link show on the Proxmox host.\n"
            "  Common values: enp3s0, eno1, eth0",
            classes="muted")
        yield Static("")
        yield Input(value=S.network_iface, placeholder="enp3s0", id="i-iface")

    def handle_next(self, app):
        S.network_iface = self.query_one("#i-iface", Input).value.strip() or "enp3s0"
        app._go(StepRootPassword())

    def handle_back(self, app): app._go(StepDeployerUser())


# ── step 4 — passwords (split) ──────────────────────────────────────────────

class StepRootPassword(Step):
    STEP_NUM = 4

    def compose(self) -> ComposeResult:
        yield Label("◆  proxmox root password", classes="title")
        yield Rule()
        yield Static(
            "[bold #cb4b16]ROOT password of your Proxmox server[/bold #cb4b16]\n\n"
            "  Used ONCE to install the SSH key on first connection.\n"
            "  The password is NOT stored anywhere.\n\n"
            "  Leave empty to be prompted during deployment.",
            classes="muted", markup=True)
        yield Static("")
        yield Input(password=True, placeholder="leave empty to skip", id="i-rootpw")
        yield Label("", id="e-rootpw", classes="err")
        yield LoadingIndicator(id="spin-rootpw")

    def on_mount(self):
        self.query_one("#spin-rootpw").display = False

    def handle_next(self, app):
        pw = self.query_one("#i-rootpw", Input).value
        S.proxmox_root_pw = pw
        if pw:
            self.query_one("#spin-rootpw").display = True
            self.query_one("#e-rootpw", Label).update("")
            self._test_pw(pw)
        else:
            app._go(StepSudoPassword())

    @work(thread=True)
    def _test_pw(self, pw):
        ok = False
        try:
            env = os.environ.copy()
            env["SSHPASS"] = pw
            env.pop("SSH_AUTH_SOCK", None)  # ignore ssh-agent keys
            r = subprocess.run(
                ["sshpass", "-e", "ssh",
                 "-o", "StrictHostKeyChecking=accept-new",
                 "-o", "IdentitiesOnly=yes",
                 "-o", "PreferredAuthentications=password",
                 "-o", "PubkeyAuthentication=no",
                 "-o", "ConnectTimeout=5",
                 "-F", "/dev/null",  # ignore ~/.ssh/config
                 f"root@{S.proxmox_address}", "true"],
                env=env, capture_output=True, timeout=10)
            ok = r.returncode == 0
        except Exception:
            pass

        def _show(ok=ok):
            self.query_one("#spin-rootpw").display = False
            if ok:
                self.query_one("#e-rootpw", Label).update("")
                self.app._go(StepSudoPassword())
            else:
                self.query_one("#e-rootpw", Label).update(
                    "✗ could not authenticate — check password or server access")
        self.app.call_from_thread(_show)

    def handle_back(self, app): app._go(StepNetwork())


class StepSudoPassword(Step):
    STEP_NUM = 4

    def compose(self) -> ComposeResult:
        yield Label("◆  sudo password", classes="title")
        yield Rule()
        yield Static(
            f"[bold #cb4b16]Sudo password for {S.deployer_user} on the deployer-cli[/bold #cb4b16]\n\n"
            "  Needed to install packages (apt), configure services.\n"
            "  Leave empty if your user has passwordless sudo (NOPASSWD).",
            classes="muted", markup=True)
        yield Static("")
        yield Input(password=True, placeholder="leave empty to skip", id="i-sudopw")
        yield Label("", id="e-sudopw", classes="err")
        yield LoadingIndicator(id="spin-sudopw")

    def on_mount(self):
        self.query_one("#spin-sudopw").display = False

    def handle_next(self, app):
        pw = self.query_one("#i-sudopw", Input).value
        S.sudo_pw = pw
        if pw and S.deployer_ip in ("127.0.0.1", "localhost"):
            self.query_one("#spin-sudopw").display = True
            self.query_one("#e-sudopw", Label).update("")
            self._test_sudo(pw)
        elif S.deployer_ip not in ("127.0.0.1", "localhost"):
            app._go(StepDeployerPassword())
        else:
            S.deployer_cli_pw = ""
            app._go(StepReview())

    @work(thread=True)
    def _test_sudo(self, pw):
        ok = False
        try:
            r = subprocess.run(
                ["sudo", "-S", "-k", "true"],
                input=pw + "\n", capture_output=True, text=True, timeout=5)
            ok = r.returncode == 0
        except Exception:
            pass

        def _show(ok=ok):
            self.query_one("#spin-sudopw").display = False
            if ok:
                self.query_one("#e-sudopw", Label).update("")
                if S.deployer_ip not in ("127.0.0.1", "localhost"):
                    self.app._go(StepDeployerPassword())
                else:
                    S.deployer_cli_pw = ""
                    self.app._go(StepReview())
            else:
                self.query_one("#e-sudopw", Label).update(
                    "✗ sudo authentication failed — check password")
        self.app.call_from_thread(_show)

    def handle_back(self, app): app._go(StepRootPassword())


class StepDeployerPassword(Step):
    STEP_NUM = 4

    def compose(self) -> ComposeResult:
        yield Label("◆  deployer-cli SSH password", classes="title")
        yield Rule()
        yield Static(
            f"  SSH password for {S.deployer_user}@{S.deployer_ip}.\n\n"
            "  The deployer-cli is a remote machine. Ansible needs SSH access.\n"
            "  Leave empty if SSH key access is already configured.",
            classes="muted")
        yield Static("")
        yield Input(password=True, placeholder="leave empty to skip", id="i-clipw")

    def handle_next(self, app):
        S.deployer_cli_pw = self.query_one("#i-clipw", Input).value
        app._go(StepReview())

    def handle_back(self, app): app._go(StepSudoPassword())


# ── step 5 — review & confirm ─────────────────────────────────────────────────
class StepReview(Step):
    STEP_NUM   = 5
    NEXT_LABEL = "Confirm →"

    def _pw_status(self, pw, empty_msg): return "provided" if pw else empty_msg

    def compose(self) -> ComposeResult:
        yield Label("◆  review your configuration", classes="title")
        yield Rule()
        yield RichLog(id="review-log", highlight=False, markup=True)
        yield Static("")
        yield Label(
            f"  files will be created at: inventories/{S.codename}/",
            classes="hint")

    def on_mount(self):
        pw  = self._pw_status(S.proxmox_root_pw, "not set (will prompt)")
        spw = self._pw_status(S.sudo_pw,         "not set (NOPASSWD)")
        dpw = ("localhost (no SSH needed)"
               if S.deployer_ip in ("127.0.0.1","localhost")
               else self._pw_status(S.deployer_cli_pw, "not set (key auth)"))
        log = self.query_one("#review-log", RichLog)
        for label, value in [
            ("codename",        S.codename),
            ("proxmox address", S.proxmox_address),
            ("proxmox node",    S.proxmox_node),
            ("scenario",        S.scenario),
            ("deployer user",   S.deployer_user),
            ("deployer IP",     S.deployer_ip),
            ("network iface",   S.network_iface),
            ("root password",   pw),
            ("sudo password",   spw),
            ("deployer access", dpw),
        ]:
            log.write(f"  [bold #268bd2]{label:20}[/bold #268bd2]  [bold #e2e8f0]{value}[/bold #e2e8f0]")

    def handle_next(self, app): app._go(StepDeploy())
    def handle_back(self, app): app._go(StepSudoPassword())


# ── step 6 — create inventory + optional deploy ───────────────────────────────
class StepDeploy(Step):
    STEP_NUM  = 6
    SHOW_BACK = False

    def compose(self) -> ComposeResult:
        yield Label("◆  creating inventory", classes="title", id="deploy-title")
        yield Rule()
        # overwrite confirmation — shown only if dest dir exists
        with Vertical(id="overwrite-confirm"):
            yield Static("")
            yield Label("", id="ow-msg", classes="warn")
            yield Static("")
            with Horizontal():
                yield Button("  Yes, overwrite  ", id="b-overwrite", classes="-ok")
                yield Button("  Cancel  ",         id="b-cancel-ow", classes="-danger")
        yield RichLog(id="log", highlight=True, markup=True)
        # deploy choice shown after inventory creation
        with Horizontal(id="deploy-btns"):
            yield Button("Deploy now →",        id="b-deploy", classes="-ok")
            yield Button("Exit  (deploy later)", id="b-exit")

    def on_mount(self):
        self.query_one("#overwrite-confirm").display = False
        self.query_one("#deploy-btns").display       = False
        self.app.query_one("#btn-next", Button).display = False
        dest = INVENTORIES / S.codename
        if dest.exists():
            self.query_one("#ow-msg", Label).update(
                f"  ⚠  inventories/{S.codename}/  already exists.\n\n"
                f"  This will overwrite the existing configuration.")
            self.query_one("#overwrite-confirm").display = True
        else:
            self.create_inventory()

    @on(Button.Pressed, "#b-overwrite")
    def do_overwrite(self):
        self.query_one("#overwrite-confirm").display = False
        self.create_inventory()

    @on(Button.Pressed, "#b-cancel-ow")
    def cancel_overwrite(self): self.app._go(StepReview())

    # ── inventory creation ────────────────────────────────────────────────────
    @work(thread=True)
    def create_inventory(self):
        import time, shutil as sh

        def log_row(badge, msg, kv=""):
            cols = {"PASS":"#4ade80","WARN":"#fbbf24","FAIL":"#f87171","INFO":"#38bdf8"}
            c = cols.get(badge, "#94a3b8")
            self.app.call_from_thread(
                lambda b=badge,m=msg,k=kv,col=c:
                    self.query_one("#log", RichLog).write(
                        f"[bold {col}]{b:6}[/bold {col}]  {m}  [dim]{k}[/dim]"))

        dest = INVENTORIES / S.codename
        try:
            if dest.exists():
                sh.rmtree(dest)
                log_row("INFO", f"removed previous configuration", f"path={dest.name}")
            sh.copytree(EXAMPLE_DIR, dest)
            log_row("PASS", "created", f"path=inventories/{S.codename}/")
        except PermissionError as e:
            log_row("FAIL", f"permission denied: {e}")
            return
        except Exception as e:
            log_row("FAIL", f"failed to create inventory: {e}")
            return
        time.sleep(0.1)

        hosts = dest / "hosts.yml"
        vars_ = dest / "group_vars" / "all" / "vars.yml"
        scen  = dest / "group_vars" / S.scenario

        sed_f(hosts, "ds-px-off-black-pxtesting", S.codename)
        sed_f(hosts, "ds-px-off-black-pxtesting.skate-eagle.ts.net:8006",
              f"{S.proxmox_address}:8006")
        sed_f(hosts, 'ansible_host: "127.0.0.1"', f'ansible_host: "{S.deployer_ip}"')
        sed_f(hosts, 'ansible_user: "grml"',       f'ansible_user: "{S.deployer_user}"')
        if S.deployer_ip not in ("127.0.0.1","localhost"):
            hosts.write_text("\n".join(
                l for l in hosts.read_text().splitlines()
                if "ansible_connection: local" not in l))
        log_row("PASS", "configured hosts.yml",
                f"proxmox={S.proxmox_address}  deployer={S.deployer_ip}")
        time.sleep(0.1)

        for old, new in [
            ('INFRASTRUCTURE_CODENAME: "to_define"',        f'INFRASTRUCTURE_CODENAME: "{S.codename}"'),
            ('INFRASTRUCTURE_PROXMOX_ADDRESS: "to_define"', f'INFRASTRUCTURE_PROXMOX_ADDRESS: "{S.proxmox_address}"'),
            ('proxmox_node: "to_define"',                   f'proxmox_node: "{S.proxmox_node}"'),
            ('proxmox_api_host: "to_define"',               f'proxmox_api_host: "{S.proxmox_address}:8006"'),
            ('infrastructure_proxmox_default_network_card_interface: "enp3s0"',
             f'infrastructure_proxmox_default_network_card_interface: "{S.network_iface}"'),
            ('DEPLOYER_CLI_USER: "grml"',      f'DEPLOYER_CLI_USER: "{S.deployer_user}"'),
            ('deployer_cli_ip: "127.0.0.1"',   f'deployer_cli_ip: "{S.deployer_ip}"'),
            ('ssh_client__dst_config_dir: "/home/grml/.ssh"',
             f'ssh_client__dst_config_dir: "/home/{S.deployer_user}/.ssh"'),
        ]:
            sed_f(vars_, old, new)
        log_row("PASS", "configured vars.yml",
                f"codename={S.codename}  node={S.proxmox_node}  iface={S.network_iface}")
        time.sleep(0.1)

        if S.scenario != "demo_lab" and (dest/"group_vars"/"demo_lab").exists():
            (dest/"group_vars"/"demo_lab").rename(scen)
        sv = scen / "vars.yml"
        if sv.exists():
            sed_f(sv, 'INFRASTRUCTURE_SCENARIO: "demo_lab"',
                  f'INFRASTRUCTURE_SCENARIO: "{S.scenario}"')
        log_row("PASS", "configured scenario", f"name={S.scenario}")
        log_row("PASS", "vault template ready", "file=vault.yml.example")
        time.sleep(0.2)

        self.app.call_from_thread(self._show_deploy_choice)

    def _show_deploy_choice(self):
        log = self.query_one("#log", RichLog)
        log.write("")
        log.write("[bold #38bdf8]◆  what you need to do next[/bold #38bdf8]")
        log.write("")
        log.write(
            f"  [bold #fbbf24]TODO[/bold #fbbf24]  create your vault secrets file:\n\n"
            f"  cp inventories/{S.codename}/group_vars/{S.scenario}/vault.yml.example \\\n"
            f"     inventories/{S.codename}/group_vars/{S.scenario}/vault.yml\n\n"
            f"  Edit vault.yml — fill in your passwords and secrets.\n"
            f"  Then encrypt it:\n\n"
            f"  ansible-vault encrypt \\\n"
            f"    inventories/{S.codename}/group_vars/{S.scenario}/vault.yml\n\n"
            f"  The vault.yml.example file has comments explaining each field.")
        log.write("")
        log.write("[dim]─────────────────────────────────────────────────────[/dim]")
        log.write("")
        log.write("[bold #38bdf8]◆  deploy now?[/bold #38bdf8]")
        log.write("")
        log.write(
            "  Deploy now will run all 3 playbooks in sequence:\n"
            "    1. generate credentials  (SSH keys, vault)\n"
            "    2. configure proxmox     (root SSH, jump user, API token)\n"
            "    3. deploy deployer-cli   (packages, workspace, SSH config)\n\n"
            f"  Note: step 2 needs the Proxmox root password for SSH setup.\n"
            f"  Root password: {'provided' if S.proxmox_root_pw else 'not set (will prompt during deploy)'}")
        log.write("")
        self.query_one("#deploy-btns").display = True

    # ── deploy choice buttons ─────────────────────────────────────────────────
    @on(Button.Pressed, "#b-exit")
    def exit_later(self):
        S.deploy_now = False
        self.app.exit()

    @on(Button.Pressed, "#b-deploy")
    def start_deploy(self):
        S.deploy_now = True
        self.app.exit()

    def handle_next(self, app): app.exit()


# ── App ────────────────────────────────────────────────────────────────────────
class Range42(App):
    TITLE    = "RANGE42  ·  infrastructure setup  v2.1.0"
    CSS      = CSS
    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=True),
        Binding("up", "focus_previous", "up", show=False, priority=False),
        Binding("down", "focus_next", "down", show=False, priority=False),
        Binding("t", "cycle_theme", "theme", show=True),
    ]

    _theme_idx: int = 0

    def action_quit(self): self.exit()

    def action_cycle_theme(self):
        self._theme_idx = (self._theme_idx + 1) % len(R42_THEMES)
        self.theme = R42_THEMES[self._theme_idx].name

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            yield Sidebar(id="sidebar")
            with Vertical(id="content-wrap"):
                yield ScrollableContainer(id="content")
                with Horizontal(id="btn-row"):
                    yield Button("← Back",    id="btn-back")
                    yield Button("Continue →", id="btn-next", classes="-ok")
        yield Footer()

    def on_mount(self):
        for t in R42_THEMES:
            self.register_theme(t)
        self.theme = R42_THEMES[2].name
        self._theme_idx = 2
        self._go(StepPreflight())

    def _go(self, step: Step):
        content = self.query_one("#content", ScrollableContainer)
        content.remove_children()
        content.mount(step)
        self.query_one("#sidebar", Sidebar).step = step.STEP_NUM
        btn_back = self.query_one("#btn-back", Button)
        btn_next = self.query_one("#btn-next", Button)
        btn_back.display  = step.SHOW_BACK
        btn_back.disabled = False
        btn_next.display  = True
        btn_next.disabled = False
        btn_next.label    = step.NEXT_LABEL
        btn_next.remove_class("-ok", "-danger")
        if step.NEXT_CLASS:
            btn_next.add_class(step.NEXT_CLASS)

    @on(Button.Pressed, "#btn-next")
    def on_next(self):
        steps = list(self.query_one("#content").children)
        if steps: steps[0].handle_next(self)

    @on(Button.Pressed, "#btn-back")
    def on_back(self):
        steps = list(self.query_one("#content").children)
        if steps: steps[0].handle_back(self)


def _print_ok(msg):   print(f"  \033[1;32m   OK  \033[0m {msg}")
def _print_fail(msg): print(f"  \033[1;31m  FAIL \033[0m {msg}")
def _print_info(msg): print(f"  \033[1;34m  INFO \033[0m {msg}")
def _print_cmd(msg):  print(f"  \033[36m       {msg}\033[0m")
def _print_bold(msg): print(f"\n  \033[1;32m  ##  {msg}\033[0m\n")


def post_wizard():
    """Runs after Textual exits — deploy in native terminal."""
    if not S.codename:
        return  # wizard was cancelled

    print()
    _print_bold("range42 setup complete")
    _print_ok(f"inventory created: inventories/{S.codename}/")
    print()

    if not S.deploy_now:
        _print_info("to deploy later, run:")
        _print_cmd("")
        _print_cmd(f"ansible-playbook site.yml \\")
        _print_cmd(f"  -i inventories/{S.codename}/hosts.yml \\")
        _print_cmd(f"  -e INFRASTRUCTURE_SCENARIO={S.scenario}")
        print()
        return

    # ── deploy now — native terminal ──
    _print_bold("starting deployment")

    env = os.environ.copy()
    extra = []

    if S.proxmox_root_pw:
        env["SSHPASS"] = S.proxmox_root_pw
        env["ANSIBLE_SSH_PASS"] = S.proxmox_root_pw
        _print_ok("proxmox root password provided")
    else:
        _print_info("proxmox root password not set — you will be prompted")

    if S.deployer_ip not in ("127.0.0.1", "localhost") and S.deployer_cli_pw:
        extra += ["-e", f"ansible_ssh_pass={S.deployer_cli_pw}"]
        _print_ok("deployer-cli password provided")

    if S.sudo_pw:
        extra += ["-e", f"ansible_become_pass={S.sudo_pw}"]
        _print_ok("sudo password provided")
    else:
        _print_info("sudo password not set — assuming NOPASSWD")

    existing_roles_path = env.get('ANSIBLE_ROLES_PATH', '')
    env["ANSIBLE_ROLES_PATH"] = f"{SCRIPT_DIR}/roles" + (f":{existing_roles_path}" if existing_roles_path else "")

    print()
    _print_info(f"running: ansible-playbook site.yml -i inventories/{S.codename}/hosts.yml")
    print()

    rc = subprocess.run(
        ["ansible-playbook", "site.yml",
         "-i", f"inventories/{S.codename}/hosts.yml",
         "-e", f"INFRASTRUCTURE_SCENARIO={S.scenario}",
         "-e", "context_ssh_keys_use_passphrase=NO",
         *extra],
        cwd=str(SCRIPT_DIR), env=env
    ).returncode

    # clear passwords
    S.proxmox_root_pw = S.sudo_pw = S.deployer_cli_pw = ""

    print()
    if rc == 0:
        _print_bold("deployment complete")
        _print_ok("credentials generated")
        _print_ok("proxmox configured")
        _print_ok("deployer-cli deployed")
        print()
        print("  ---- first time setup ----")
        print()
        _print_info("activate your workspace:")
        _print_cmd(f"range42-context use {S.codename} {S.scenario}")
        print()
        _print_info("check everything is ready:")
        _print_cmd("range42-context status")
        print()
        _print_info("deploy the lab VMs:")
        _print_cmd("range42-context deploy")
        print()
        print("  ---- daily operations ----")
        print()
        _print_info("fast redeploy (VMs only, skip templates):")
        _print_cmd("range42-context delete-vms")
        _print_cmd("range42-context deploy-vms")
        print()
        _print_info("full reset (delete all + recreate):")
        _print_cmd("range42-context reset")
        print()
        _print_info("quick ssh to a VM:")
        _print_cmd("range42-context ssh wazuh")
        print()
        _print_info("all commands:")
        _print_cmd("range42-context help")
        print()
        print("  ---- add another infrastructure ----")
        print()
        _print_cmd("range42-context init")
        print()
    else:
        _print_bold("deployment failed")
        _print_fail("check the error above and re-run:")
        _print_cmd("")
        _print_cmd(f"ansible-playbook site.yml \\")
        _print_cmd(f"  -i inventories/{S.codename}/hosts.yml \\")
        _print_cmd(f"  -e INFRASTRUCTURE_SCENARIO={S.scenario}")
        print()


if __name__ == "__main__":
    Range42().run()
    post_wizard()
