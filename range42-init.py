#!/usr/bin/env python3
"""
range42-init.py  —  interactive infrastructure setup  (Textual edition)

  Install : pip install textual
  Run     : python3 range42-init.py
"""

import json, os, re, shlex, shutil, subprocess, ssl, sys, urllib.request
from pathlib import Path

# make wizard/ importable
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# force truecolor — SSH doesn't forward COLORTERM, causing Textual
# to fall back to 16-color ANSI palette (ugly DOS blue)
os.environ.setdefault("COLORTERM", "truecolor")

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
        Input, Label, LoadingIndicator, RichLog, Select, Static, Rule, Switch,
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

    # check if existing venv is healthy (python can import sys)
    if _venv.exists() and _python.exists():
        _test = subprocess.run(
            [str(_python), "-c", "import sys; print(sys.executable)"],
            capture_output=True, text=True,
        )
        if _test.returncode != 0:
            # venv is broken (missing ensurepip / python3-venv) — remove and retry
            import shutil as _sh
            _sh.rmtree(str(_venv), ignore_errors=True)

    if not _venv.exists():
        print()
        print("  \033[1;33mINFO\033[0m  textual library not found — creating local venv...")
        print()
        try:
            import ensurepip  # noqa: F401 — test availability before venv creation
        except ImportError:
            print("  \033[1;31mFAIL\033[0m  python3-venv is not installed")
            print()
            print("  fix:  sudo apt-get install python3-venv")
            print("  then: python3 range42-init.py")
            print()
            sys.exit(1)
        try:
            import venv
            venv.create(str(_venv), with_pip=True)
        except Exception:
            import shutil as _sh
            _sh.rmtree(str(_venv), ignore_errors=True)
            print("  \033[1;31mFAIL\033[0m  could not create python venv")
            print()
            print("  fix:  sudo apt-get install python3-venv")
            print("  then: python3 range42-init.py")
            print()
            sys.exit(1)
        # verify venv is healthy after creation
        _test = subprocess.run(
            [str(_pip), "--version"], capture_output=True, text=True,
        )
        if _test.returncode != 0:
            import shutil as _sh
            _sh.rmtree(str(_venv), ignore_errors=True)
            print("  \033[1;31mFAIL\033[0m  venv created but pip is broken (missing python3-venv?)")
            print()
            print("  fix:  sudo apt install python3-venv")
            print("  then: python3 range42-init.py")
            print()
            sys.exit(1)
        print("  \033[1;33mINFO\033[0m  installing textual (pip install textual)...")
        print("        do NOT use: apt install python3-textual (version too old)")
        print()
        r = subprocess.run([str(_pip), "install", "--quiet", "textual"], check=False)
        if r.returncode != 0:
            print("  \033[1;31mFAIL\033[0m  pip install textual failed")
            print()
            print("  fix:  " + str(_pip) + " install textual")
            print()
            sys.exit(1)

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

from textual import work, on
from rich.text import Text

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent.resolve()
INVENTORIES = SCRIPT_DIR / "inventories"
EXAMPLE_DIR = INVENTORIES / "example"
# range42-playbooks lives as a sibling of the range42 repo on the operator machine.
# preflight auto-clones it if missing (see wizard/preflight.py:ensure_playbooks_repo).
PLAYBOOKS_DIR = SCRIPT_DIR.parent / "range42-playbooks"

def list_deployable_scenarios():
    """
    Return sorted list of scenario names in range42-playbooks/scenarios/ that
    have a complete templates/ dir (all 4 required template files present).
    Scenarios starting with '_' are treated as non-deployable placeholders.
    """
    scenarios_dir = PLAYBOOKS_DIR / "scenarios"
    if not scenarios_dir.exists():
        return []
    out = []
    for d in sorted(scenarios_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        tmpl = d / "templates"
        if tmpl.is_dir() and all((tmpl / f).exists() for f in SCENARIO_REQUIRED_FILES):
            out.append(d.name)
    return out

# ── wizard cache (XDG-compliant, survives reboot) ─────────────────────────────
# Used to remember non-sensitive wizard inputs across runs (e.g. last apt proxy URL).
# Never store credentials, vault contents, or anything per-codename here.
_WIZARD_CACHE_DIR  = os.path.expanduser("~/.cache/range42")
_WIZARD_CACHE_FILE = os.path.join(_WIZARD_CACHE_DIR, "wizard.json")


def _load_wizard_cache() -> dict:
    """Return cached wizard inputs as a dict. Silent fallback to {} on any error."""
    try:
        with open(_WIZARD_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
        return {}


def _save_wizard_cache(updates: dict) -> None:
    """Merge `updates` into the cache file. Silent fail if write impossible."""
    try:
        os.makedirs(_WIZARD_CACHE_DIR, exist_ok=True)
        cache = _load_wizard_cache()
        cache.update(updates)
        with open(_WIZARD_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except (PermissionError, OSError):
        pass  # caching is best-effort, never block the wizard


# ── state ──────────────────────────────────────────────────────────────────────
class _S:
    codename        = ""
    proxmox_address = ""
    proxmox_node    = "pve"
    scenario        = "blank_scenario_2_subnets"
    deployer_user   = os.environ.get("USER", "")
    deployer_ip     = "127.0.0.1"
    network_iface   = "enp3s0"
    proxmox_root_pw = ""
    sudo_pw         = ""
    deployer_cli_pw = ""
    setup_mode      = "new"
    preflight_ok    = False
    deploy_now      = False
    install_dir     = os.path.expanduser("~/range42")
    nat_interface   = "vmbr0"
    apt_proxy_url   = _load_wizard_cache().get("apt_proxy_url", "")

    def __init__(self):
        self.nat_bridges = {f"vmbr{i}": True for i in range(140, 152)}
S = _S()


# ── apt proxy validation helpers ──────────────────────────────────────────────

# Format: http(s)://host:port  (host can be IP or hostname; port is required)
_APT_PROXY_RE = re.compile(r'^https?://[A-Za-z0-9._\-]+:\d+/?$')


def _validate_apt_proxy_url(url: str) -> bool:
    """Return True if url matches http(s)://host:port format."""
    return bool(_APT_PROXY_RE.match(url))


def _check_apt_proxy_reachable(url: str, timeout: float = 5.0):
    """
    Test reachability of an apt proxy URL via HTTP HEAD.
    Returns (ok: bool, msg: str). 4xx/5xx counts as reachable (server responding).
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, str(e.reason)
    except (TimeoutError, OSError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# ── preflight (extracted to wizard/preflight.py) ──────────────────────────────
from wizard.preflight import run_all_checks, get_apt_install_command, get_apt_install_packages, SCENARIO_REQUIRED_FILES

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

/* Select dropdown — keep narrow so the ▼ arrow indicator stays visible */
Select        { background: $surface; border: tall $panel; color: $foreground; width: 40; }
Select:focus  { border: tall $primary; }

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
#path-choices Button { min-width: 60; margin-bottom: 1; }
#overwrite-confirm  { height: auto; margin-bottom: 1; align: center middle; content-align: center middle; }
.warn               { color: $accent; }
"""

# ── sidebar (table of contents) ────────────────────────────────────────────────
STEPS = [
    (0, "welcome"),
    (0, "apt proxy"),
    (0, "prerequisites"),
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


# ── step 0 — apt proxy (optional) ─────────────────────────────────────────────
class StepAptProxy(Step):
    STEP_NUM  = 0
    SHOW_BACK = True  # back to welcome

    def handle_back(self, app):
        app._go(StepWelcome())

    def compose(self) -> ComposeResult:
        yield Label("◆  step 0 — apt proxy (optional)", classes="title")
        yield Rule()
        yield Static(
            "  If you have a local apt cache (apt-cacher-ng, Squid, etc.), enter\n"
            "  its URL here. It will be used to speed up apt-get installs on:\n"
            "    - the deployer-cli (during system bootstrap)\n"
            "    - the Proxmox host (cloud-init cicustom snippet for VM templates)\n"
            "    - all lab VMs (inherited via cloud-init from templates)\n\n"
            "  Format: full URL with protocol AND port\n"
            "  Examples:\n"
            "    http://192.168.1.50:3142     (apt-cacher-ng default port)\n"
            "    http://192.168.1.100:80      (proxy on port 80)\n\n"
            "  Leave empty to disable. Reachability is checked on Continue.",
            classes="muted")
        yield Static("")
        yield Input(value=S.apt_proxy_url, placeholder="(empty = no proxy)", id="i-apt-proxy")
        yield Static("", id="apt-proxy-status", classes="muted")

    def handle_next(self, app):
        url = self.query_one("#i-apt-proxy", Input).value.strip()
        status = self.query_one("#apt-proxy-status", Static)

        # empty = OK, no proxy
        if not url:
            S.apt_proxy_url = ""
            _save_wizard_cache({"apt_proxy_url": ""})
            app._go(StepPreflight())
            return

        # validate format
        if not _validate_apt_proxy_url(url):
            status.update(
                "[FAIL] invalid format — expected http(s)://host:port  "
                "(e.g. http://192.168.1.50:3142)"
            )
            return

        # reachability check
        status.update(f"[INFO] checking reachability of {url} ...")
        ok, msg = _check_apt_proxy_reachable(url)
        if not ok:
            status.update(f"[FAIL] not reachable: {msg}")
            return

        # validation passed — persist for next runs
        S.apt_proxy_url = url
        _save_wizard_cache({"apt_proxy_url": url})
        app._go(StepPreflight())


# ── step 0 — preflight ────────────────────────────────────────────────────────
class StepPreflight(Step):
    STEP_NUM  = 0
    SHOW_BACK = True

    def handle_back(self, app):
        app._go(StepAptProxy())

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
        results, fail = run_all_checks(EXAMPLE_DIR)
        for r in results:
            self.app.call_from_thread(self._row, r["badge"], r["label"], r["detail"])
            time.sleep(0.12)

        self._apt_cmd = get_apt_install_command(results)
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
            # show "Install prerequisites" button only if sudo is available and there are packages to install
            if self._apt_cmd and shutil.which("sudo"):
                btn_row = self.app.query_one("#btn-row", Horizontal)
                btn_row.mount(Button("Install prerequisites", id="btn-install", classes="-ok"))

    def handle_next(self, app):
        if not S.preflight_ok: app.exit(); return
        app._go(StepInstallPaths())


# ── step 0a — install paths ──────────────────────────────────────────────────
class StepInstallPaths(Step):
    STEP_NUM  = 0
    SHOW_BACK = True

    def _tree_text(self, git_dir):
        """Build a preview of the directory structure."""
        cfg_dir = os.path.expanduser("~/range42.config")
        return (
            f"  {git_dir}/\n"
            f"  ├── range42/                      main repo (this wizard)\n"
            f"  ├── range42-playbooks/             scenarios + bundles\n"
            f"  ├── range42-catalog/               ansible roles + docker stacks\n"
            f"  ├── range42-ansible_roles-proxmox_controller/\n"
            f"  ├── range42-ansible_roles-debug-devkit/\n"
            f"  ├── range42-backend-api/\n"
            f"  └── range42-deployer-ui/\n"
            f"\n"
            f"  {cfg_dir}/\n"
            f"  └── <codename>-<scenario>/         workspace (secrets, keys, inventory)\n"
        )

    def compose(self) -> ComposeResult:
        yield Label("◆  install paths", classes="title")
        yield Rule()
        yield Static(
            "  Where should range42 repos be cloned on the deployer-cli?\n\n"
            "  Note: workspace config (secrets, keys, inventory) is always\n"
            "  stored in ~/range42.config/ — this path cannot be changed.\n",
            classes="muted")
        yield Container(id="path-choices")
        yield Static("")
        yield Static(self._tree_text(S.install_dir), id="path-preview")
        yield Container(id="custom-inputs")

    def on_mount(self):
        lst = self.query_one("#path-choices")
        lst.mount(Button(
            "  ◆  recommended  —  ~/range42  +  ~/range42.config",
            id="p-recommended", classes="-ok"))
        lst.mount(Button(
            "  ↺  custom path",
            id="p-custom", classes="-danger"))
        # hide custom input initially
        self.query_one("#custom-inputs").display = False

    @on(Button.Pressed, "#p-recommended")
    def pick_recommended(self):
        S.install_dir = os.path.expanduser("~/range42")
        self.query_one("#custom-inputs").display = False
        self.query_one("#path-preview", Static).update(
            self._tree_text(S.install_dir))

    @on(Button.Pressed, "#p-custom")
    def pick_custom(self):
        box = self.query_one("#custom-inputs")
        if box.display:
            return  # already visible
        box.display = True
        current_dir = str(SCRIPT_DIR)
        box.mount(Label("  repos directory:", classes="muted"))
        box.mount(Input(value=current_dir, id="input-install-dir"))
        S.install_dir = current_dir
        self.query_one("#path-preview", Static).update(
            self._tree_text(S.install_dir))

    @on(Input.Changed)
    def on_input_change(self, event: Input.Changed):
        """Update preview tree in real time when user types."""
        try:
            git_dir = self.query_one("#input-install-dir", Input).value.strip().rstrip("/")
        except Exception:
            return
        S.install_dir = git_dir
        self.query_one("#path-preview", Static).update(
            self._tree_text(git_dir))

    def handle_next(self, app):
        try:
            S.install_dir = self.query_one("#input-install-dir", Input).value.strip().rstrip("/")
        except Exception:
            pass  # recommended mode — input not mounted, use S value as-is
        app._go(StepExisting() if existing() else StepCodename())

    def handle_back(self, app):
        app._go(StepPreflight())


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
            gv = INVENTORIES / cfg / "group_vars"
            scenarios = []
            if gv.exists():
                scenarios = [d.name for d in sorted(gv.iterdir()) if d.is_dir() and d.name != "all"]
            if scenarios:
                for sc in scenarios:
                    lst.mount(Button(
                        f"  ↺  {cfg}  —  {sc}  —  overwrite existing configuration",
                        id=f"c-{cfg}--{sc}"))
            else:
                lst.mount(Button(
                    f"  ↺  {cfg}  —  overwrite existing configuration",
                    id=f"c-{cfg}"))

    @on(Button.Pressed)
    def pick(self, e: Button.Pressed):
        bid = e.button.id or ""
        if not bid.startswith("c-"): return
        mode = bid[2:].split("--")[0]
        S.setup_mode = mode
        if mode != "new":
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', mode):
                return  # reject invalid names silently (button was created from filesystem, shouldn't happen)
            prefill(mode)
        self.app._go(StepCodename())


# ── step 1 — welcome ──────────────────────────────────────────────────────────
class StepWelcome(Step):
    STEP_NUM  = 0
    SHOW_BACK = False  # very first step

    def compose(self) -> ComposeResult:
        yield Label("◆  range42  —  setup wizard", classes="title")
        yield Rule()
        yield Static("""\
  Welcome to range42.

  range42 deploys reproducible cyber range labs on Proxmox via Ansible.
  This wizard configures the initial setup of a new lab environment.

  Steps:
    0. apt proxy (optional, speeds up package downloads)
    1. prerequisites checks
    2. Proxmox connection (host address, node)
    3. scenario + deployer-cli configuration
    4. credentials (Proxmox root, sudo, deployer-cli)
    5. review + optional one-shot deployment

  You will need:
    - Your Proxmox server address (IP or FQDN)
    - The Proxmox node name (visible in the Proxmox web UI)
    - root and sudo passwords for Proxmox + deployer-cli

  Press Continue to start, or Ctrl+C to quit at any time.
  Every step has a Back button so you can correct earlier inputs.""", classes="muted")

    def handle_next(self, app): app._go(StepAptProxy())


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

    def handle_back(self, app):
        app._go(StepExisting() if existing() else StepInstallPaths())


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
        app._go(StepRootPassword())

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

    def handle_next(self, app): app._go(StepAutoDetectNAT())
    def handle_back(self, app): app._go(StepSudoPassword())


# ── step 2c — auto-detect NAT interface ──────────────────────────────────────
class StepAutoDetectNAT(Step):
    STEP_NUM  = 2
    SHOW_BACK = True

    def compose(self) -> ComposeResult:
        yield Label("◆  NAT outbound interface", classes="title")
        yield Rule()
        yield Static(
            "  Detecting the outbound network interface on your Proxmox server.\n"
            "  This is the interface VMs will use for internet access (NAT).\n",
            classes="muted")
        yield LoadingIndicator(id="nat-spin")
        yield Label("", id="nat-result")
        yield Static("")
        yield Label("  NAT interface:", classes="muted")
        yield Input(value=S.nat_interface, placeholder="vmbr0", id="i-nat-iface")

    def on_mount(self):
        self.app.query_one("#btn-next", Button).disabled = True
        self._detect()

    @work(thread=True)
    def _detect(self):
        detected = "vmbr0"
        internet_ok = False
        try:
            if S.proxmox_root_pw:
                env = os.environ.copy()
                env["SSHPASS"] = S.proxmox_root_pw
                env.pop("SSH_AUTH_SOCK", None)
                r = subprocess.run(
                    ["sshpass", "-e", "ssh",
                     "-o", "StrictHostKeyChecking=accept-new",
                     "-o", "ConnectTimeout=5",
                     f"root@{S.proxmox_address}",
                     "ip route | grep default | awk '{print $5}'"],
                    env=env, capture_output=True, text=True, timeout=10)
                if r.returncode == 0 and r.stdout.strip():
                    detected = r.stdout.strip()
                # test internet via detected interface
                r2 = subprocess.run(
                    ["sshpass", "-e", "ssh",
                     "-o", "StrictHostKeyChecking=accept-new",
                     "-o", "ConnectTimeout=5",
                     f"root@{S.proxmox_address}",
                     "ping -c1 -W3 1.1.1.1 >/dev/null 2>&1 && echo OK || echo FAIL"],
                    env=env, capture_output=True, text=True, timeout=15)
                internet_ok = "OK" in r2.stdout
            else:
                # no root password — can't SSH, use default
                detected = "vmbr0"
        except Exception as exc:
            detected = "vmbr0"
            _exc_msg = str(exc)  # available for UI if needed

        S.nat_interface = detected

        def _show():
            self.query_one("#nat-spin").display = False
            r = self.query_one("#nat-result", Label)
            self.query_one("#i-nat-iface", Input).value = detected
            if internet_ok:
                r.update(
                    f"\n  [bold #4ade80]✓[/bold #4ade80]  detected: {detected} — internet reachable")
            elif S.proxmox_root_pw:
                r.update(
                    f"\n  [bold #fbbf24]![/bold #fbbf24]  detected: {detected} — could not verify internet\n"
                    "  NAT may need manual configuration after deployment.")
            else:
                r.update(
                    f"\n  [bold #fbbf24]![/bold #fbbf24]  no root password — using default: {detected}\n"
                    "  Auto-detection requires root SSH access.")
            self.app.query_one("#btn-next", Button).disabled = False
        self.app.call_from_thread(_show)

    def handle_next(self, app):
        S.nat_interface = self.query_one("#i-nat-iface", Input).value.strip() or "vmbr0"
        app._go(StepNATBridges())

    def handle_back(self, app):
        app._go(StepProxmoxCheck())


# ── step 2d — NAT per bridge ─────────────────────────────────────────────────
class StepNATBridges(Step):
    STEP_NUM  = 2
    SHOW_BACK = True

    def compose(self) -> ComposeResult:
        yield Label("◆  NAT per bridge", classes="title")
        yield Rule()
        yield Static(
            "  Enable or disable outbound NAT (internet access) per bridge.\n"
            "  Click a bridge to toggle NAT on/off.\n",
            classes="muted")
        yield Horizontal(id="nat-columns")

    def _btn_label(self, name, enabled):
        idx = name.replace("vmbr", "")
        status = "active " if enabled else "disabled"
        return f" {status}  {name}  .{idx}.0/24"

    def on_mount(self):
        cols = self.query_one("#nat-columns")
        bridges = sorted(S.nat_bridges.keys())
        # 3 columns of 4
        for col_idx in range(3):
            col = Vertical()
            for row_idx in range(4):
                i = col_idx * 4 + row_idx
                if i < len(bridges):
                    name = bridges[i]
                    enabled = S.nat_bridges[name]
                    btn = Button(
                        self._btn_label(name, enabled),
                        id=f"nat-{name}",
                        classes="-ok" if enabled else "-danger")
                    col.compose_add_child(btn)
            cols.mount(col)

    @on(Button.Pressed)
    def on_toggle(self, event: Button.Pressed):
        bid = event.button.id or ""
        if not bid.startswith("nat-"):
            return
        name = bid.replace("nat-", "")
        S.nat_bridges[name] = not S.nat_bridges[name]
        enabled = S.nat_bridges[name]
        event.button.label = self._btn_label(name, enabled)
        event.button.remove_class("-ok", "-danger")
        event.button.add_class("-ok" if enabled else "-danger")

    def handle_next(self, app):
        app._go(StepScenario())

    def handle_back(self, app):
        app._go(StepAutoDetectNAT())


# ── step 3 — scenario, deployer, network (split) ─────────────────────────────

class StepScenario(Step):
    STEP_NUM = 3

    def compose(self) -> ComposeResult:
        yield Label("◆  step 2/3  —  scenario", classes="title")
        yield Rule()
        yield Static(
            "  Which lab scenario to deploy on this infrastructure.\n\n"
            "  blank_scenario_2_subnets is the minimal lab (4 VMs on 2 subnets) — default.\n"
            "  demo_lab is the full cyber range with admin + student + vulnerable hosts.\n\n"
            "  Pick from the list of deployable scenarios in range42-playbooks.",
            classes="muted")
        yield Static("")

        scenarios = list_deployable_scenarios()
        if scenarios:
            # pre-select current S.scenario if valid, else blank_scenario_2_subnets, else first available
            if S.scenario in scenarios:
                initial = S.scenario
            elif "blank_scenario_2_subnets" in scenarios:
                initial = "blank_scenario_2_subnets"
            else:
                initial = scenarios[0]
            yield Select(
                [(s, s) for s in scenarios],
                value=initial,
                allow_blank=False,
                id="i-scenario",
            )
        else:
            # defensive fallback — preflight should have caught this
            yield Static(
                "  [FAIL] no deployable scenarios found in range42-playbooks.\n"
                "  Re-run preflight to auto-clone the repo.",
                classes="muted")
            yield Input(value=S.scenario, placeholder="blank_scenario_2_subnets", id="i-scenario")

    def handle_next(self, app):
        w = self.query_one("#i-scenario")
        if isinstance(w, Select):
            S.scenario = w.value if w.value is not Select.BLANK else "blank_scenario_2_subnets"
        else:
            S.scenario = w.value.strip() or "blank_scenario_2_subnets"
        app._go(StepDeployerIP())

    def handle_back(self, app): app._go(StepNATBridges())


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
        S.deployer_cli_pw = S.sudo_pw  # reuse sudo password for deployer SSH (single-machine assumption)
        app._go(StepReview())

    def handle_back(self, app): app._go(StepDeployerIP())



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
        exc_detail = ""
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
        except Exception as exc:
            ok = False
            exc_detail = f"{type(exc).__name__}: {exc}"

        def _show(ok=ok, exc_detail=exc_detail):
            self.query_one("#spin-rootpw").display = False
            if ok:
                self.query_one("#e-rootpw", Label).update("")
                self.app._go(StepSudoPassword())
            else:
                msg = "✗ could not authenticate"
                if exc_detail:
                    msg += f" — {exc_detail}"
                else:
                    msg += " — check password or server access"
                self.query_one("#e-rootpw", Label).update(msg)
        self.app.call_from_thread(_show)

    def handle_back(self, app): app._go(StepNode())


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
        if pw:
            self.query_one("#spin-sudopw").display = True
            self.query_one("#e-sudopw", Label).update("")
            self._test_sudo(pw)
        else:
            app._go(StepProxmoxCheck())

    @work(thread=True)
    def _test_sudo(self, pw):
        ok = False
        exc_detail = ""
        try:
            r = subprocess.run(
                ["sudo", "-S", "-k", "true"],
                input=pw + "\n", capture_output=True, text=True, timeout=5)
            ok = r.returncode == 0
        except Exception as exc:
            ok = False
            exc_detail = f"{type(exc).__name__}: {exc}"

        def _show(ok=ok, exc_detail=exc_detail):
            self.query_one("#spin-sudopw").display = False
            if ok:
                self.query_one("#e-sudopw", Label).update("")
                self.app._go(StepProxmoxCheck())
            else:
                msg = "✗ sudo authentication failed"
                if exc_detail:
                    msg += f" — {exc_detail}"
                else:
                    msg += " — check password"
                self.query_one("#e-sudopw", Label).update(msg)
        self.app.call_from_thread(_show)

    def handle_back(self, app): app._go(StepRootPassword())




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
            ("NAT interface",   S.nat_interface),
            ("NAT bridges",     ", ".join(n for n, v in sorted(S.nat_bridges.items()) if v)),
            ("root password",   pw),
            ("sudo password",   spw),
            ("deployer access", dpw),
        ]:
            log.write(f"  [bold #268bd2]{label:20}[/bold #268bd2]  [bold #e2e8f0]{value}[/bold #e2e8f0]")

    def handle_next(self, app): app._go(StepDeploy())
    def handle_back(self, app): app._go(StepDeployerUser())


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
                yield Button("  Yes, update  ", id="b-overwrite", classes="-ok")
                yield Button("  Cancel  ",      id="b-cancel-ow", classes="-danger")
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
                f"  This will refresh hosts.yml + group_vars/all/vars.yml with current values.\n"
                f"  Existing scenario configs (group_vars/<scenario>/) are preserved.")
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
        scenario_tmpl = PLAYBOOKS_DIR / "scenarios" / S.scenario / "templates"

        # validate the scenario: dir must exist AND contain all 4 required template files
        # (replaces the old copytree(demo_lab) fallback — each scenario is now authoritative)
        if not scenario_tmpl.exists():
            log_row("FAIL", f"scenario '{S.scenario}' not found in range42-playbooks",
                    f"expected dir: {scenario_tmpl}")
            return
        missing = [f for f in SCENARIO_REQUIRED_FILES if not (scenario_tmpl / f).exists()]
        if missing:
            log_row("FAIL", f"scenario '{S.scenario}' is incomplete",
                    f"missing in templates/: {', '.join(missing)}")
            return

        was_new = not dest.exists()
        try:
            # create skeleton: hosts.yml + group_vars/all/ only
            # scenario group_vars are populated further down from playbooks templates
            (dest / "group_vars" / "all").mkdir(parents=True, exist_ok=True)
            sh.copy2(EXAMPLE_DIR / "hosts.yml", dest / "hosts.yml")
            sh.copy2(EXAMPLE_DIR / "group_vars" / "all" / "vars.yml",
                     dest / "group_vars" / "all" / "vars.yml")
            log_row("PASS", "created" if was_new else "updated",
                    f"path=inventories/{S.codename}/")
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

        sed_f(hosts, "my-proxmox", S.codename)
        sed_f(hosts, "proxmox.example.com:8006",
              f"{S.proxmox_address}:8006")
        sed_f(hosts, 'ansible_host: "127.0.0.1"', f'ansible_host: "{S.deployer_ip}"')
        sed_f(hosts, 'ansible_user: "your_deployer_cli_username"', f'ansible_user: "{S.deployer_user}"')
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
            ('infrastructure_proxmox_default_network_card_interface: "vmbr0"',
             f'infrastructure_proxmox_default_network_card_interface: "{S.nat_interface}"'),
            ('DEPLOYER_CLI_USER: "your_deployer_cli_username"', f'DEPLOYER_CLI_USER: "{S.deployer_user}"'),
            ('deployer_cli_ip: "127.0.0.1"',   f'deployer_cli_ip: "{S.deployer_ip}"'),
            ('DEPLOYER_CLI__DST_GIT_DIR: "/home/your_deployer_cli_username/range42/"',
             f'DEPLOYER_CLI__DST_GIT_DIR: "{S.install_dir}/"'),
            ('DEPLOYER_CLI__DST_CONFIG_BASE_DIR: "/home/your_deployer_cli_username/range42.config"',
             f'DEPLOYER_CLI__DST_CONFIG_BASE_DIR: "/home/{S.deployer_user}/range42.config"'),
            ('ssh_client__dst_config_dir: "/home/your_deployer_cli_username/.ssh"',
             f'ssh_client__dst_config_dir: "/home/{S.deployer_user}/.ssh"'),
            ('apt_proxy_url: ""', f'apt_proxy_url: "{S.apt_proxy_url}"'),
        ]:
            sed_f(vars_, old, new)
        # inject range42_lab_bridges with NAT toggles
        bridges_yaml = "\n\n# lab bridges NAT configuration (managed by wizard)\nrange42_lab_bridges:\n"
        for name in sorted(S.nat_bridges.keys()):
            idx = name.replace("vmbr", "")
            ip = f"192.168.{idx}.1"
            nat = "true" if S.nat_bridges[name] else "false"
            bridges_yaml += f'  - {{ name: "{name}", ip: "{ip}", nat: {nat} }}\n'
        with open(vars_, "a") as f:
            f.write(bridges_yaml)

        log_row("PASS", "configured vars.yml",
                f"codename={S.codename}  node={S.proxmox_node}  nat={S.nat_interface}")
        time.sleep(0.1)

        # populate scenario group_vars from range42-playbooks/scenarios/<s>/templates/
        #   ansible-vars.yml   → vars.yml          (renamed back to Ansible convention)
        #   vault-example.yml  → vault.yml.example (same rename pattern)
        # if the scenario dir already exists (re-run on same codename+scenario),
        # preserve ALL existing files — user may have edited vars.yml or filled vault.yml.
        if not scen.exists():
            scen.mkdir(parents=True, exist_ok=True)
            sh.copy2(scenario_tmpl / "ansible-vars.yml",  scen / "vars.yml")
            sh.copy2(scenario_tmpl / "vault-example.yml", scen / "vault.yml.example")
            log_row("PASS", "configured scenario", f"name={S.scenario}")
        else:
            log_row("PASS", "preserved scenario", f"name={S.scenario} (existing config untouched)")
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
        self._go(StepWelcome())

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

    @on(Button.Pressed, "#btn-install")
    def on_install(self):
        """Exit TUI, run apt install, then re-launch the wizard."""
        steps = list(self.query_one("#content").children)
        if steps and hasattr(steps[0], "_apt_cmd"):
            self._install_cmd = steps[0]._apt_cmd
        self.exit()


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
        _print_cmd(f"  -e @inventories/{S.codename}/group_vars/{S.scenario}/vars.yml \\")
        _print_cmd(f"  -e INFRASTRUCTURE_SCENARIO={S.scenario} \\")
        _print_cmd(f"  -e context_ssh_keys_use_passphrase=NO")
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

    # -e @<scenario_vars_file> loads scenario-specific variables as extra vars.
    # Without this, Ansible silently ignores inventories/<cn>/group_vars/<scenario>/vars.yml
    # because no inventory group matches the scenario name — role defaults would win,
    # and user edits to vars.yml would have no effect on deployed VMs.
    # Placed FIRST so the wizard's scalar -e overrides below still take precedence.
    scenario_vars_file = f"inventories/{S.codename}/group_vars/{S.scenario}/vars.yml"
    rc = subprocess.run(
        ["ansible-playbook", "site.yml",
         "-i", f"inventories/{S.codename}/hosts.yml",
         "-e", f"@{scenario_vars_file}",
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
        _print_info(f"repos cloned to:     {S.install_dir}/")
        _print_info(f"workspace config in: ~/range42.config/")
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

        # if current shell is bash and zsh is available, switch to zsh
        # so range42-context works immediately
        current_shell = os.environ.get("SHELL", "")
        zsh_path = shutil.which("zsh")
        if "/bash" in current_shell and zsh_path:
            _print_info("switching to zsh (required for range42-context)...")
            print()
            os.execv(zsh_path, [zsh_path, "-l"])

    else:
        _print_bold("deployment failed")
        _print_fail("check the error above and re-run:")
        _print_cmd("")
        _print_cmd(f"ansible-playbook site.yml \\")
        _print_cmd(f"  -i inventories/{S.codename}/hosts.yml \\")
        _print_cmd(f"  -e @inventories/{S.codename}/group_vars/{S.scenario}/vars.yml \\")
        _print_cmd(f"  -e INFRASTRUCTURE_SCENARIO={S.scenario} \\")
        _print_cmd(f"  -e context_ssh_keys_use_passphrase=NO")
        print()


if __name__ == "__main__":
    app = Range42()
    app._install_cmd = None
    app.run()

    # post-TUI: if preflight failed and no install command, show help
    if not S.preflight_ok and not app._install_cmd:
        print()
        if not shutil.which("sudo"):
            _print_fail("sudo is not installed (required)")
            print()
            _print_info("as root, run:")
            _print_cmd("apt-get install sudo")
            _print_cmd("usermod -aG sudo <your-user>")
            print()
            _print_info("then log out and log back in, and re-run:")
            _print_cmd("python3 range42-init.py")
            print()
        sys.exit(1)

    # post-TUI: if user clicked "Install prerequisites", run apt then re-launch
    if app._install_cmd:
        print()
        print(f"  \033[1;33mINFO\033[0m  running: {app._install_cmd}")
        print()
        rc = subprocess.call(app._install_cmd, shell=True)
        if rc == 0:
            print()
            print("  \033[1;32m   OK\033[0m  packages installed — restarting wizard...")
            print()
            # if zsh was just installed and we're in bash, restart wizard in zsh
            current_shell = os.environ.get("SHELL", "")
            zsh_path = shutil.which("zsh")
            if "/bash" in current_shell and zsh_path:
                print("  \033[1;33mINFO\033[0m  switching to zsh...")
                print()
                script_path = str(Path(__file__).resolve())
                os.execv(zsh_path, [zsh_path, "-c", "exec python3 " + shlex.quote(script_path)])
            else:
                os.execv(sys.executable, [sys.executable, __file__] + sys.argv[1:])
        else:
            print()
            print("  \033[1;31m FAIL\033[0m  install failed — run manually:")
            print(f"         {app._install_cmd}")
            print(f"         then: python3 {__file__}")
            sys.exit(1)
    post_wizard()
