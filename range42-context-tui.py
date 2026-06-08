#!/usr/bin/env python3
"""
range42-context-tui.py  -  Textual TUI for range42-context

  Launched via : range42-context --tui
  Wrapper      : the --tui case branch in range42-context.sh creates a
                 sentinel file, runs this script in a while loop, and
                 eval's the sentinel content in the parent shell on exit 42.

  Architecture (locked) : Option C / hybrid
    - stream-safe commands run as zsh subprocesses streamed into a RichLog
    - `use` is the only command that exits the TUI (code 42) so the outer
      zsh wrapper can mutate the parent shell environment
    - `cd` is hidden from the menu (subprocess cd does nothing observable)

  See TUI_TASK.md for the full design.
"""

import os, sys, signal, subprocess, shlex, json, re, time, socket, pty
from dataclasses import dataclass, field
from pathlib import Path


EXIT_QUIT = 0
EXIT_EVAL = 42


# SSH does not forward COLORTERM
os.environ.setdefault("COLORTERM", "truecolor")


# The bootstrap MUST only trigger when textual is absent entirely. If a specific
# submodule import fails inside the actual import block below, we WANT a real
# traceback - silently re-execing into the same broken venv would loop forever.
try:
    import textual as _textual_probe  # noqa: F401
except ImportError:
    _venv = Path(__file__).parent / ".venv-wizard"
    _pip = _venv / "bin" / "pip"
    _python = _venv / "bin" / "python3"

    if _venv.exists() and _python.exists():
        _test = subprocess.run(
            [str(_python), "-c", "import sys"], capture_output=True, text=True,
        )
        if _test.returncode != 0:
            import shutil as _sh
            _sh.rmtree(str(_venv), ignore_errors=True)

    if not _venv.exists():
        print()
        print("  \033[1;33mINFO\033[0m  textual library not found - creating local venv...")
        print()
        try:
            import ensurepip  # noqa: F401
        except ImportError:
            print("  \033[1;31mFAIL\033[0m  python3-venv is not installed")
            print()
            print("  fix:  sudo apt-get install python3-venv")
            print("  then: python3 range42-context-tui.py")
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
            print("  then: python3 range42-context-tui.py")
            print()
            sys.exit(1)
        _test = subprocess.run(
            [str(_pip), "--version"], capture_output=True, text=True,
        )
        if _test.returncode != 0:
            import shutil as _sh
            _sh.rmtree(str(_venv), ignore_errors=True)
            print("  \033[1;31mFAIL\033[0m  venv created but pip is broken (missing python3-venv?)")
            print()
            print("  fix:  sudo apt install python3-venv")
            print("  then: python3 range42-context-tui.py")
            print()
            sys.exit(1)
        print("  \033[1;33mINFO\033[0m  installing textual (pip install textual)...")
        print("        do NOT use: apt install python3-textual (version too old)")
        print("        first run downloads ~5-10 MB ; subsequent runs are instant")
        print()
        r = subprocess.run([str(_pip), "install", "--progress-bar", "on", "textual"], check=False)
        if r.returncode != 0:
            print()
            print("  \033[1;31mFAIL\033[0m  pip install textual failed")
            print()
            print("  fix:  " + str(_pip) + " install textual")
            print()
            sys.exit(1)
        print()
        print("  \033[1;32mOK\033[0m    textual installed, launching TUI...")
        print()

    if _python.exists():
        os.execv(str(_python), [str(_python), __file__] + sys.argv[1:])
    else:
        print()
        print("  \033[1;31mERROR\033[0m  failed to create venv for textual.")
        print()
        print("  Manual install:")
        print("    \033[36mpython3 -m venv .venv-wizard && .venv-wizard/bin/pip install textual\033[0m")
        print("    \033[36m.venv-wizard/bin/python3 range42-context-tui.py\033[0m")
        sys.exit(1)


from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import (
    Header, Footer, OptionList, RichLog, Input, ListView, ListItem, Label, Static,
)
from textual.widgets.option_list import Option

from textual import work, on
from rich.text import Text


# ── themes (verbatim from range42-init.py:161-177) ────────────────────────────
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


STATE_PATH = Path.home() / ".cache" / "range42-context-tui-state.json"

# Parent dir of all workspaces. The env var is RANGE42_CONFIG_BASE_DIR (single
# underscore between BASE and DIR). NOT RANGE42_CONFIG__ROOT_DIR — that one
# points to the ACTIVE workspace root, not its parent.
CONFIG_BASE_DIR = Path(os.environ.get(
    "RANGE42_CONFIG_BASE_DIR",
    str(Path.home() / "range42.config"),
))


def _sentinel_path() -> Path:
    return Path(os.environ.get("RANGE42_TUI_SENTINEL", "/tmp/range42-tui-eval.sh"))


def _find_catalog_root():
    """Locate the range42-catalog clone, mirroring _r42_catalog_try_list."""
    candidates = [
        os.environ.get("RANGE42_INVENTORY", ""),
        os.path.join(os.environ.get("RANGE42_GITDIR__ROOT_DIR", ""), "range42-catalog"),
        str(Path.home() / "range42" / "range42-catalog"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return Path(c)
    return None


def _list_catalog_elements():
    """
    Walk range42-catalog/NN_*_layer/ and return [(layer_name, rel_path, level)]
    for deployable elements (containing compose.yml / docker-compose.yml /
    Makefile). level is "L2" if the dir carries catalog_try.yml else "L1".
    Skips paths under */roles/* (ansible role internals).
    """
    root = _find_catalog_root()
    if not root:
        return []
    layer_re = re.compile(r"^[0-9]+_.*_layer$")
    deploy_files = ("compose.yml", "docker-compose.yml", "Makefile")
    results = []
    try:
        for layer_dir in sorted(root.iterdir()):
            if not layer_dir.is_dir() or not layer_re.match(layer_dir.name):
                continue
            for sub in layer_dir.rglob("*"):
                if not sub.is_dir():
                    continue
                if "/roles/" in str(sub):
                    continue
                if not any((sub / f).is_file() for f in deploy_files):
                    continue
                rel = str(sub.relative_to(layer_dir))
                level = "L2" if (sub / "catalog_try.yml").is_file() else "L1"
                results.append((layer_dir.name, rel, level))
    except (OSError, FileNotFoundError):
        return []
    return results


# ── command catalog ───────────────────────────────────────────────────────────
@dataclass
class CommandSpec:
    id: str
    category: str                 # workspace | operations | lifecycle | info | catalog-try
    label: str
    description: str
    dispatch: str                 # 'subprocess' | 'suspend' | 'eval-on-exit'
    arg_ui: str = "none"          # 'none' | 'workspace-picker' | 'arg-input'
    args_required: list = field(default_factory=list)
    args_optional: list = field(default_factory=list)


COMMANDS: list = [
    # workspace
    # `list` is intentionally hidden from the TUI menu : the `use` picker
    # already shows all available workspaces in a richer two-column view.
    # `range42-context list` remains callable from the shell directly.
    CommandSpec("use",     "workspace", "use",     "switch to a workspace",             "eval-on-exit", arg_ui="workspace-picker"),
    CommandSpec("status",  "workspace", "status",  "check workspace health",            "subprocess"),
    CommandSpec("init",    "workspace", "init",    "launch setup wizard",               "suspend"),
    CommandSpec("current", "workspace", "current", "show active workspace",             "subprocess"),
    # operations
    CommandSpec("deploy",            "operations", "deploy",            "run full scenario setup (templates + VMs)", "subprocess"),
    CommandSpec("deploy-vms",        "operations", "deploy-vms",        "deploy VMs only (skip templates)",          "subprocess"),
    CommandSpec("delete",            "operations", "delete",            "delete all scenario VMs + templates",       "subprocess"),
    CommandSpec("delete-vms",        "operations", "delete-vms",        "delete VMs only (keep templates)",          "subprocess"),
    CommandSpec("delete-everything", "operations", "delete-everything", "delete ALL VMs+templates across scenarios", "suspend"),
    CommandSpec("reset",             "operations", "reset",             "delete + recreate all VMs",                 "subprocess"),
    CommandSpec("ssh-reload",        "operations", "ssh-reload",        "reload SSH keys for active workspace",      "subprocess"),
    # lifecycle
    CommandSpec("start",         "lifecycle", "start",         "start all scenario VMs",          "subprocess"),
    CommandSpec("stop",          "lifecycle", "stop",          "graceful shutdown of all VMs",    "subprocess"),
    CommandSpec("stop-force",    "lifecycle", "stop-force",    "force stop all scenario VMs",     "subprocess"),
    CommandSpec("pause",         "lifecycle", "pause",         "pause all scenario VMs",          "subprocess"),
    CommandSpec("resume",        "lifecycle", "resume",        "resume all paused scenario VMs",  "subprocess"),
    CommandSpec("snapshot",      "lifecycle", "snapshot",      "snapshot all scenario VMs",       "subprocess", arg_ui="arg-input", args_optional=["name"]),
    CommandSpec("snapshot-list", "lifecycle", "snapshot-list", "list snapshots of all scenario VMs", "subprocess"),
    CommandSpec("revert",        "lifecycle", "revert",        "revert all scenario VMs to a snapshot", "subprocess", arg_ui="arg-input", args_required=["name"]),
    # info
    CommandSpec("show-vault",     "info", "show-vault",     "show ansible vault contents (decrypted)", "subprocess"),
    CommandSpec("show-config",    "info", "show-config",    "show workspace orientation",              "subprocess"),
    CommandSpec("show-inventory", "info", "show-inventory", "show ansible inventory tree",             "subprocess"),
    # CommandSpec("ssh",            "info", "ssh",            "quick ssh to a VM by name",               "suspend", arg_ui="arg-input", args_required=["pattern"]),
    CommandSpec("debug",          "info", "debug",          "toggle verbose ansible output",           "subprocess"),
    # CommandSpec("help",           "info", "help",           "show range42-context help",               "subprocess"),
    # catalog-try
    CommandSpec("catalog-try",             "catalog-try", "catalog-try",             "deploy + smoke-check a catalog element", "suspend", arg_ui="catalog-picker", args_required=["path"]),
    CommandSpec("catalog-try-list",        "catalog-try", "catalog-try-list",        "list catalog-try elements (no admin)",   "subprocess"),
    CommandSpec("catalog-try-list-admin",  "catalog-try", "catalog-try-list-admin",  "list catalog-try elements (admin only)", "subprocess"),
]

CATEGORY_ORDER = ["workspace", "operations", "lifecycle", "info", "catalog-try"]


# ── workspace picker helpers ──────────────────────────────────────────────────
def _parse_workspace_dir(workspace_dir: Path):
    """
    Return (codename, scenario) for a workspace directory by reading
    sourced_range42.sh, falling back to a heuristic on the directory name.
    Returns None if the directory does not look like a workspace.
    """
    sourced = workspace_dir / "sourced_range42.sh"
    if sourced.is_file():
        try:
            txt = sourced.read_text(errors="replace")
        except OSError:
            txt = ""
        cn = re.search(r'^\s*export\s+RANGE42_CODENAME=["\']?([^"\'\s]+)', txt, re.M)
        sc = re.search(r'^\s*export\s+RANGE42_SCENARIO=["\']?([^"\'\s]+)', txt, re.M)
        if cn and sc:
            return cn.group(1), sc.group(1)
    # heuristic : split on last "-" where right side matches snake_case
    name = workspace_dir.name
    m = re.match(r"^(.+)-([a-z][a-z0-9_]*)$", name)
    if m:
        return m.group(1), m.group(2)
    return None


def _list_workspaces():
    """Walk CONFIG_BASE_DIR and return [(codename, scenario, dir_name)]."""
    results = []
    try:
        for entry in sorted(CONFIG_BASE_DIR.iterdir()):
            if not entry.is_dir():
                continue
            if "-" not in entry.name:
                continue
            parsed = _parse_workspace_dir(entry)
            if parsed:
                cn, sc = parsed
                results.append((cn, sc, entry.name))
    except (OSError, FileNotFoundError):
        return []
    return results


# ── workspace picker screen ───────────────────────────────────────────────────
class WorkspacePickerScreen(ModalScreen):
    """Modal screen for selecting <codename> <scenario> before `use`."""

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("/", "focus_filter", "filter"),
    ]

    DEFAULT_CSS = """
    WorkspacePickerScreen {
        align: center middle;
    }

    #picker-container {
        width: 90%;
        height: 80%;
        border: heavy $primary;
        padding: 1 2;
    }

    #picker-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #picker-filter {
        margin-bottom: 1;
    }

    #picker-columns {
        height: 1fr;
    }

    #cn-list, #sc-list {
        border: solid $surface;
        width: 1fr;
        height: 100%;
    }

    .picker-col-label {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }

    .picker-hint {
        color: $foreground 60%;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._pairs = []
        self._codenames = []
        self._current = None  # (codename, scenario) of active workspace
        self._filter = ""
        self._cn_idx = 0      # tracked internally, not read from cn_list.index
        self._scenarios_for_cn = []  # scenarios shown in the right column

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-container"):
            yield Static("range42-context  -  pick workspace", id="picker-title")
            yield Input(placeholder="filter (codename OR scenario, substring, case-insensitive)", id="picker-filter")
            with Horizontal(id="picker-columns"):
                with Vertical():
                    yield Static("codename", classes="picker-col-label")
                    yield ListView(id="cn-list")
                with Vertical():
                    yield Static("scenario", classes="picker-col-label", id="sc-label")
                    yield ListView(id="sc-list")
            yield Static("Tab swap   /  filter   Enter pick   Esc back", classes="picker-hint")

    def on_mount(self) -> None:
        self._pairs = _list_workspaces()
        self._current = self._detect_current()
        self._rebuild_codename_list()
        if self._codenames:
            self._cn_idx = self._initial_codename_index()
            cn_list = self.query_one("#cn-list", ListView)
            try:
                cn_list.index = self._cn_idx
            except Exception:
                pass
            self._refresh_scenarios()
            self.query_one("#sc-list", ListView).focus()
        else:
            self.query_one("#picker-filter", Input).focus()

    def _detect_current(self):
        """Read RANGE42_CODENAME / RANGE42_SCENARIO from environment if set."""
        cn = os.environ.get("RANGE42_CODENAME")
        sc = os.environ.get("RANGE42_SCENARIO")
        if cn and sc:
            return (cn, sc)
        return None

    def _initial_codename_index(self) -> int:
        if self._current and self._current[0] in self._codenames:
            return self._codenames.index(self._current[0])
        return 0

    def _filtered_pairs(self):
        """
        Apply the case-insensitive substring filter on BOTH codename and
        scenario. A pair matches if the needle appears in either field.
        Returns [(codename, scenario)].
        """
        if not self._filter:
            return [(cn, sc) for cn, sc, _dn in self._pairs]
        needle = self._filter.lower()
        return [
            (cn, sc) for cn, sc, _dn in self._pairs
            if needle in cn.lower() or needle in sc.lower()
        ]

    def _filtered_codenames(self):
        cn_set = []
        for cn, _sc in self._filtered_pairs():
            if cn not in cn_set:
                cn_set.append(cn)
        return sorted(cn_set)

    def _rebuild_codename_list(self) -> None:
        cn_list = self.query_one("#cn-list", ListView)
        cn_list.clear()
        self._codenames = self._filtered_codenames()
        if not self._codenames:
            if not self._pairs:
                cn_list.append(ListItem(Label("No workspaces available")))
            else:
                cn_list.append(ListItem(Label("no match")))
            return
        for cn in self._codenames:
            marker = " *" if self._current and cn == self._current[0] else "  "
            cn_list.append(ListItem(Label(f"{marker} {cn}")))

    def _refresh_scenarios(self) -> None:
        sc_list = self.query_one("#sc-list", ListView)
        sc_list.clear()
        self._scenarios_for_cn = []
        if not self._codenames:
            self.query_one("#sc-label", Static).update("scenario")
            return
        try:
            selected_cn = self._codenames[self._cn_idx]
        except IndexError:
            return
        # If the filter matches the codename itself, show ALL its scenarios.
        # Otherwise, show only the scenarios that match the filter (so the
        # operator sees just the relevant ones, e.g. typing "kunai" reveals
        # the kunai_lab scenario under hv-bw without scrolling).
        needle = self._filter.lower() if self._filter else ""
        if needle and needle in selected_cn.lower():
            scenarios = sorted({sc for cn, sc, _dn in self._pairs if cn == selected_cn})
        elif needle:
            scenarios = sorted({
                sc for cn, sc, _dn in self._pairs
                if cn == selected_cn and needle in sc.lower()
            })
        else:
            scenarios = sorted({sc for cn, sc, _dn in self._pairs if cn == selected_cn})
        label = "scenario"
        if self._current and self._current[0] == selected_cn:
            label = f"scenario  (active: {self._current[1]})"
        self.query_one("#sc-label", Static).update(label)
        self._scenarios_for_cn = scenarios
        if not scenarios:
            sc_list.append(ListItem(Label("No scenarios for this codename")))
            return
        active_sc_idx = 0
        for i, sc in enumerate(scenarios):
            marker = "  "
            if self._current and self._current == (selected_cn, sc):
                marker = " *"
                active_sc_idx = i
            sc_list.append(ListItem(Label(f"{marker} {sc}")))
        try:
            sc_list.index = active_sc_idx
        except Exception:
            pass

    @on(Input.Changed, "#picker-filter")
    def _on_filter_changed(self, event: Input.Changed) -> None:
        self._filter = event.value
        self._rebuild_codename_list()
        self._refresh_scenarios()

    @on(Input.Submitted, "#picker-filter")
    def _on_filter_submitted(self, event: Input.Submitted) -> None:
        cn_list = self.query_one("#cn-list", ListView)
        if self._codenames:
            cn_list.focus()

    @on(ListView.Highlighted, "#cn-list")
    def _on_cn_highlighted(self, event: ListView.Highlighted) -> None:
        cn_list = self.query_one("#cn-list", ListView)
        if cn_list.index is not None:
            self._cn_idx = cn_list.index
        self._refresh_scenarios()

    @on(ListView.Selected, "#cn-list")
    def _on_cn_selected(self, event: ListView.Selected) -> None:
        sc_list = self.query_one("#sc-list", ListView)
        sc_list.focus()

    @on(ListView.Selected, "#sc-list")
    def _on_sc_selected(self, event: ListView.Selected) -> None:
        self._dispatch_use()

    def _dispatch_use(self) -> None:
        sc_list = self.query_one("#sc-list", ListView)
        if not self._codenames or not self._scenarios_for_cn:
            return
        try:
            codename = self._codenames[self._cn_idx]
        except IndexError:
            return
        sc_idx = sc_list.index if sc_list.index is not None else 0
        try:
            scenario = self._scenarios_for_cn[sc_idx]
        except IndexError:
            return
        payload = "range42-context use " + shlex.quote(codename) + " " + shlex.quote(scenario) + "\n"
        try:
            _sentinel_path().write_text(payload)
        except OSError as exc:
            self.app._log_line(f"[error] cannot write sentinel: {exc}")
            return
        # pass EXIT_EVAL positionally so it becomes the return value of app.run()
        # (the `return_code=` kwarg is newer textual API and may be ignored on
        # older installs - leading to python exiting with code 0 and the zsh
        # wrapper breaking its eval loop without re-launching).
        self.app.exit(EXIT_EVAL)

    def action_back(self) -> None:
        self.dismiss(None)

    def action_focus_filter(self) -> None:
        self.query_one("#picker-filter", Input).focus()


# ── catalog-try picker screen ─────────────────────────────────────────────────
class CatalogTryPickerScreen(ModalScreen):
    """Modal screen for picking a catalog element to run with `catalog-try`."""

    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("/", "focus_filter", "filter"),
    ]

    DEFAULT_CSS = """
    CatalogTryPickerScreen {
        align: center middle;
    }

    #catalog-container {
        width: 90%;
        height: 80%;
        border: heavy $primary;
        padding: 1 2;
    }

    #catalog-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #catalog-filter {
        margin-bottom: 1;
    }

    #catalog-list {
        height: 1fr;
        border: solid $surface;
    }

    .catalog-hint {
        color: $foreground 60%;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._elements = []
        self._filtered = []
        self._filter = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="catalog-container"):
            yield Static("range42-context catalog-try  -  pick a catalog element", id="catalog-title")
            yield Input(placeholder="filter (substring on layer or path, case-insensitive)", id="catalog-filter")
            yield ListView(id="catalog-list")
            yield Static("Enter pick   /  filter   Esc back", classes="catalog-hint")

    def on_mount(self) -> None:
        self._elements = _list_catalog_elements()
        # exclude docker/admin/* by default (matches catalog-try-list default scope)
        self._elements = [e for e in self._elements if not e[1].startswith("docker/admin/")]
        self._refresh_list()
        if self._filtered:
            self.query_one("#catalog-list", ListView).focus()
        else:
            self.query_one("#catalog-filter", Input).focus()

    def _refresh_list(self) -> None:
        listv = self.query_one("#catalog-list", ListView)
        listv.clear()
        needle = self._filter.lower()
        if needle:
            self._filtered = [
                (layer, p, lvl) for layer, p, lvl in self._elements
                if needle in p.lower() or needle in layer.lower()
            ]
        else:
            self._filtered = list(self._elements)
        if not self._filtered:
            if not self._elements:
                listv.append(ListItem(Label("No catalog elements found - is range42-catalog cloned?")))
            else:
                listv.append(ListItem(Label("no match")))
            return
        # pad the path column so the [layer] tags align in a right column
        max_path_len = max((len(p) for _, p, _ in self._filtered), default=0)
        for layer, p, lvl in self._filtered:
            tag = "[L2]" if lvl == "L2" else "[L1]"
            padded_path = p.ljust(max_path_len + 4)
            listv.append(ListItem(Label(f"  {tag}  {padded_path}[{layer}]")))

    @on(Input.Changed, "#catalog-filter")
    def _on_filter_changed(self, event: Input.Changed) -> None:
        self._filter = event.value
        self._refresh_list()

    @on(Input.Submitted, "#catalog-filter")
    def _on_filter_submitted(self, event: Input.Submitted) -> None:
        if self._filtered:
            self.query_one("#catalog-list", ListView).focus()

    @on(ListView.Selected, "#catalog-list")
    def _on_element_selected(self, event: ListView.Selected) -> None:
        listv = self.query_one("#catalog-list", ListView)
        if not self._filtered:
            return
        idx = listv.index if listv.index is not None else 0
        try:
            _layer, path, _lvl = self._filtered[idx]
        except IndexError:
            return
        self.dismiss(path)

    def action_back(self) -> None:
        self.dismiss(None)

    def action_focus_filter(self) -> None:
        self.query_one("#catalog-filter", Input).focus()


# ── arg-input modal (for ssh / revert / snapshot / etc.) ──────────────────────
class ArgInputScreen(ModalScreen):
    """Simple single-Input modal that collects a required free-text arg."""

    BINDINGS = [
        Binding("escape", "back", "back"),
    ]

    DEFAULT_CSS = """
    ArgInputScreen {
        align: center middle;
    }

    #arg-container {
        width: 70%;
        height: auto;
        border: heavy $primary;
        padding: 1 2;
    }

    #arg-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #arg-hint {
        color: $foreground 60%;
        margin-top: 1;
    }
    """

    def __init__(self, cmd: CommandSpec):
        super().__init__()
        self.cmd = cmd
        self._required = list(cmd.args_required)
        self._optional = list(cmd.args_optional)

    def compose(self) -> ComposeResult:
        if self._required:
            arg = self._required[0]
            title = f"range42-context {self.cmd.id}  -  enter {arg} (required)"
            placeholder = arg
        else:
            arg = self._optional[0] if self._optional else "args"
            title = f"range42-context {self.cmd.id}  -  enter {arg} (optional, leave blank to skip)"
            placeholder = arg
        with Vertical(id="arg-container"):
            yield Static(title, id="arg-title")
            yield Input(placeholder=placeholder, id="arg-input")
            yield Static("Enter run   Esc cancel", id="arg-hint")

    def on_mount(self) -> None:
        self.query_one("#arg-input", Input).focus()

    @on(Input.Submitted, "#arg-input")
    def _on_submit(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if self._required and not value:
            # required arg empty -> keep modal open, no-op
            return
        self.dismiss(value)

    def action_back(self) -> None:
        self.dismiss(None)


# ── main application ──────────────────────────────────────────────────────────
class ContextTUI(App):
    TITLE = "range42-context  -  TUI"

    BINDINGS = [
        Binding("ctrl+c",   "quit",                "quit",  show=True),
        Binding("q",        "quit",                "quit",  show=True),
        Binding("ctrl+l",   "clear_log",           "clear", show=True),
        Binding("ctrl+k",   "kill_running",        "stop",  show=True),
        Binding("t",        "cycle_theme",         "theme", show=True),
        Binding("question_mark", "toggle_description", "desc", show=True, key_display="?"),
    ]

    CSS = """
    Screen { layout: vertical; }

    #workspace-status {
        height: 1;
        padding: 0 1;
        background: $surface;
        text-style: bold;
    }

    #workspace-status.ws-active {
        color: $success;
    }

    #workspace-status.ws-inactive {
        color: $error;
    }

    #main { height: 1fr; }

    #cmd-pane {
        width: 75;
        border-right: solid $surface;
    }

    #cmd-list {
        height: 1fr;
    }

    #out-pane {
        width: 1fr;
    }

    #out {
        height: 1fr;
        background: $surface;
        padding: 1 2;
    }

    Header { background: $boost; }

    .title {
        text-style: bold;
        color: $accent;
        padding: 0 2;
    }

    .muted {
        color: $foreground 60%;
        padding: 0 2;
    }
    """

    # widths used by the toggle below : compact = 1/2 (descriptions hidden, default), wide = full
    CMD_PANE_WIDTH_WIDE = 75
    CMD_PANE_WIDTH_COMPACT = 38

    def __init__(self):
        super().__init__()
        self._current_proc = None
        self._cmd_by_id = {c.id: c for c in COMMANDS}
        self._theme_index = 0
        self._show_descriptions = False  # default : hide descriptions, compact pane
        self._pending_cursor_index = None  # populated by _load_state, applied by _populate_commands

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="workspace-status", classes="ws-inactive")
        with Horizontal(id="main"):
            with Vertical(id="cmd-pane"):
                yield Static("commands", classes="title")
                yield OptionList(id="cmd-list")
            with Vertical(id="out-pane"):
                yield Static("output", classes="title")
                yield RichLog(id="out", highlight=False, markup=False, wrap=False, max_lines=10000)
        yield Footer()

    def on_mount(self) -> None:
        # register themes
        for theme in R42_THEMES:
            self.register_theme(theme)
        # restore state BEFORE populating so _show_descriptions is correct
        self._load_state()
        # apply the cmd-pane width based on the restored _show_descriptions
        self._apply_cmd_pane_width()
        # populate the command list (uses self._show_descriptions)
        self._populate_commands()
        # apply the active theme
        try:
            self.theme = R42_THEMES[self._theme_index].name
        except (IndexError, AttributeError):
            self.theme = R42_THEMES[0].name
        # workspace context in the header sub-title
        self._refresh_sub_title()
        # initial banner : workspace status line first so the operator always
        # sees the active workspace immediately, especially after a `use` that
        # re-launched the TUI in a fresh process
        out = self.query_one("#out", RichLog)
        self._log_workspace_status()
        out.write("")
        if os.environ.get("RANGE42_ACTIVE_WORKSPACE"):
            out.write(Text.from_markup("[dim]press Enter on a command to run it. q to quit, Ctrl+K to stop a running command.[/]"))
        else:
            out.write(Text.from_markup("[dim]select [bold]use[/bold] to open a workspace context, then pick a command to run.[/]"))
        out.write("")

    # ─── workspace context helpers ───────────────────────────────────────────

    def _workspace_context(self):
        """
        Return (is_active: bool, prompt_line: str) for the current workspace.
        The active workspace is taken from RANGE42_ACTIVE_WORKSPACE (exported by
        _r42_use, format "codename-scenario") - NOT from RANGE42_CODENAME /
        RANGE42_SCENARIO which are workspace-scoped exports from sourced_range42.sh.
        """
        ws = os.environ.get("RANGE42_ACTIVE_WORKSPACE", "")
        user = os.environ.get("USER", "") or os.environ.get("LOGNAME", "")
        host = os.environ.get("HOSTNAME", "")
        if not host:
            try:
                host = socket.gethostname()
            except Exception:
                host = ""
        try:
            cwd = os.getcwd()
            home = str(Path.home())
            if cwd == home:
                cwd = "~"
            elif cwd.startswith(home + "/"):
                cwd = "~" + cwd[len(home):]
        except Exception:
            cwd = ""
        if ws:
            return True, f"[r42:{ws}] {user}@{host} {cwd}"
        suffix = f" - {user}@{host} {cwd}" if user and host else ""
        return False, f"no active workspace{suffix}"

    def _refresh_sub_title(self) -> None:
        """Build the prompt-style status line at the top of the screen."""
        is_active, line = self._workspace_context()
        try:
            status = self.query_one("#workspace-status", Static)
        except Exception:
            return
        if is_active:
            status.update(f"  {line}")
            status.remove_class("ws-inactive")
            status.add_class("ws-active")
            ws = os.environ.get("RANGE42_ACTIVE_WORKSPACE", "")
            self.sub_title = f"[r42:{ws}]"
        else:
            status.update(f"  {line}")
            status.remove_class("ws-active")
            status.add_class("ws-inactive")
            self.sub_title = "no active workspace"

    def _log_workspace_status(self) -> None:
        """Log the colored workspace context line into the RichLog."""
        is_active, line = self._workspace_context()
        try:
            out = self.query_one("#out", RichLog)
        except Exception:
            return
        style = "bold green" if is_active else "bold red"
        try:
            out.write(Text(line, style=style))
        except Exception:
            out.write(line)

    # ─── command list population ─────────────────────────────────────────────

    def _populate_commands(self) -> None:
        cmd_list = self.query_one("#cmd-list", OptionList)
        def _blank(suffix):
            """Empty disabled option used as a visual blank line between sections."""
            try:
                return Option(Text(""), id=f"_blank_{suffix}", disabled=True)
            except TypeError:
                return Option(Text(""), id=f"_blank_{suffix}")

        opts = []
        first = True
        for cat in CATEGORY_ORDER:
            cmds_in_cat = [c for c in COMMANDS if c.category == cat]
            if not cmds_in_cat:
                continue
            # blank line BEFORE category header (skipped for the first one)
            if not first:
                opts.append(_blank(f"pre_{cat}"))
            first = False
            # category header (disabled, non-selectable)
            try:
                opts.append(Option(
                    Text.assemble((f"  [{cat}]", "bold cyan")),
                    id=f"_cat_{cat}",
                    disabled=True,
                ))
            except TypeError:
                opts.append(Option(Text.assemble((f"  [{cat}]", "bold cyan")), id=f"_cat_{cat}"))
            # blank line AFTER category header, before commands
            opts.append(_blank(f"post_{cat}"))
            for c in cmds_in_cat:
                # 7 spaces : 2 base + 5 extra to offset commands from category headers
                if self._show_descriptions:
                    label = Text.assemble(("     ", ""), (c.label, "bold"), ("  ", ""), (c.description, "dim"))
                else:
                    label = Text.assemble(("     ", ""), (c.label, "bold"))
                opts.append(Option(label, id=c.id))
        try:
            cmd_list.add_options(opts)
        except Exception:
            for o in opts:
                try:
                    cmd_list.add_option(o)
                except Exception:
                    pass
        # set initial highlight to first navigable option (skip _cat_/_blank_/disabled)
        if cmd_list.option_count:
            for i in range(cmd_list.option_count):
                try:
                    opt = cmd_list.get_option_at_index(i)
                except Exception:
                    continue
                if getattr(opt, "disabled", False):
                    continue
                if opt.id and opt.id.startswith("_"):
                    continue
                cmd_list.highlighted = i
                break
        # apply pending cursor from _load_state (overrides initial highlight)
        if self._pending_cursor_index is not None:
            try:
                idx = int(self._pending_cursor_index)
                if 0 <= idx < cmd_list.option_count:
                    opt = cmd_list.get_option_at_index(idx)
                    if not getattr(opt, "disabled", False) and not (opt.id and opt.id.startswith("_")):
                        cmd_list.highlighted = idx
            except (ValueError, IndexError, TypeError):
                pass
            self._pending_cursor_index = None

    # ─── command dispatch ────────────────────────────────────────────────────
    @on(OptionList.OptionSelected, "#cmd-list")
    def _on_cmd_selected(self, event: OptionList.OptionSelected) -> None:
        cmd_id = event.option.id
        # ids starting with "_" (e.g. _cat_*, _blank_*) are non-navigable spacers
        if not cmd_id or cmd_id.startswith("_"):
            return
        cmd = self._cmd_by_id.get(cmd_id)
        if not cmd:
            return
        self._dispatch(cmd)

    @on(OptionList.OptionHighlighted, "#cmd-list")
    def _on_highlight_changed(self, event: OptionList.OptionHighlighted) -> None:
        self._save_state()

    def _dispatch(self, cmd: CommandSpec) -> None:
        # workspace picker for `use`
        if cmd.arg_ui == "workspace-picker":
            self.push_screen(WorkspacePickerScreen())
            return
        # catalog picker for `catalog-try`
        if cmd.arg_ui == "catalog-picker":
            def _then_catalog(path):
                if path is None:
                    return  # user cancelled
                self._run_command(cmd, [path])
            self.push_screen(CatalogTryPickerScreen(), _then_catalog)
            return
        # arg-input modal for commands needing a free-text arg
        if cmd.arg_ui == "arg-input":
            def _then(value):
                if value is None:
                    return  # user cancelled
                args = [value] if value else []
                self._run_command(cmd, args)
            self.push_screen(ArgInputScreen(cmd), _then)
            return
        # no-arg dispatch
        self._run_command(cmd, [])

    def _run_command(self, cmd: CommandSpec, args: list) -> None:
        if cmd.dispatch == "subprocess":
            self._run_subprocess(cmd, args)
        elif cmd.dispatch == "suspend":
            self._run_suspended(cmd, args)
        elif cmd.dispatch == "eval-on-exit":
            # only `use` reaches here, and it goes through the picker above
            self._log_line(f"[error] {cmd.id}: eval-on-exit without picker")

    # ─── subprocess runner (stream-safe path) ────────────────────────────────
    def _run_subprocess(self, cmd: CommandSpec, args: list) -> None:
        if self._current_proc and self._current_proc.poll() is None:
            self._log_line("[warn] another command is already running. Ctrl+K to cancel.")
            return
        self._log_separator()
        quoted_args = " ".join(shlex.quote(a) for a in args)
        full_cmd = f"range42-context {cmd.id} {quoted_args}".strip()
        self._log_workspace_status()
        self._log_line(f"> running: {full_cmd}")
        self._spawn_subprocess(cmd, args, full_cmd)

    @work(thread=True, exclusive=True, group="cmd")
    def _spawn_subprocess(self, cmd: CommandSpec, args: list, full_cmd: str) -> None:
        # RANGE42_QUIET=1 suppresses the "deployer-cli ready / load previous
        # workspace / all commands" banner that range42-context.sh prints on
        # every source. We source ~/.zshrc (not range42-context.sh directly)
        # to inherit any custom shell functions / PATH the operator added.
        #
        # Color forcing : when stdout is a pipe (our case), tools like ansible
        # detect not-a-tty and disable ANSI colors. Force them on so the
        # RichLog gets colored output via Text.from_ansi.
        env = {
            **os.environ,
            "TERM": "xterm-256color",
            "PYTHONUNBUFFERED": "1",
            "RANGE42_QUIET": "1",
            "ANSIBLE_FORCE_COLOR": "1",
            "FORCE_COLOR": "1",
            "CLICOLOR_FORCE": "1",
            "PY_COLORS": "1",
        }
        quoted_args = " ".join(shlex.quote(a) for a in args)
        shell_cmd = f"source ~/.zshrc 2>/dev/null; range42-context {cmd.id} {quoted_args}".strip()
        start = time.monotonic()
        # Provide a pty as stdin so `[ -t 0 ]` returns true in the subprocess.
        # devkit shim `devkit_proxmox.STDIN.stdin_or_jsons.to.jsons.sh` branches
        # on this test to decide between "use vault default node" (TTY) vs
        # "read piped JSON" (pipe). With stdin=DEVNULL the test returns false
        # and the script aborts silently (delete-vms / status / snapshot-list
        # become no-ops in the TUI).
        #
        # CRITICAL : master_fd MUST stay open in the parent for the whole
        # lifetime of the child. Closing master too early tears down the pty
        # session and the child's `[ -t 0 ]` flips back to false. Slave can be
        # closed immediately after Popen (the child has its own dup).
        master_fd = slave_fd = None
        try:
            master_fd, slave_fd = pty.openpty()
            stdin_arg = slave_fd
        except OSError:
            stdin_arg = subprocess.DEVNULL
        try:
            proc = subprocess.Popen(
                ["zsh", "-c", shell_cmd],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=stdin_arg,
                text=True, bufsize=1, env=env,
            )
        except (OSError, FileNotFoundError) as exc:
            for fd in (slave_fd, master_fd):
                if fd is not None:
                    try: os.close(fd)
                    except OSError: pass
            self.call_from_thread(self._log_line, f"[error] failed to spawn zsh: {exc}")
            return
        # Close slave in parent now (child holds its own dup). Keep master open
        # until proc.wait() returns - see comment above.
        if slave_fd is not None:
            try: os.close(slave_fd)
            except OSError: pass
        self._current_proc = proc
        try:
            for line in proc.stdout:
                self.call_from_thread(self._log_line, line.rstrip("\n"))
        except Exception as exc:
            self.call_from_thread(self._log_line, f"[error] stream interrupted: {exc}")
        rc = proc.wait()
        if master_fd is not None:
            try: os.close(master_fd)
            except OSError: pass
        dur = time.monotonic() - start
        self.call_from_thread(self._log_workspace_status)
        self.call_from_thread(self._log_line, f"> exit: {rc}  ({dur:.1f}s)")
        self._current_proc = None

    # ─── suspended runner (interactive path) ─────────────────────────────────
    def _run_suspended(self, cmd: CommandSpec, args: list) -> None:
        quoted_args = " ".join(shlex.quote(a) for a in args)
        full_cmd = f"range42-context {cmd.id} {quoted_args}".strip()
        self._log_separator()
        self._log_workspace_status()
        self._log_line(f"> suspending TUI for: {full_cmd}")
        # same RANGE42_QUIET + .zshrc-source pattern as _spawn_subprocess
        env = {**os.environ, "RANGE42_QUIET": "1"}
        shell_cmd = f"source ~/.zshrc 2>/dev/null; range42-context {cmd.id} {quoted_args}".strip()
        with self.suspend():
            try:
                rc = subprocess.run(["zsh", "-c", shell_cmd], check=False, env=env).returncode
            except Exception as exc:
                self._log_line(f"[error] suspended run failed: {exc}")
                return
        self._log_workspace_status()
        self._log_line(f"> resumed TUI, exit: {rc}")

    # ─── logging helpers ─────────────────────────────────────────────────────
    def _log_line(self, text: str) -> None:
        out = self.query_one("#out", RichLog)
        try:
            out.write(Text.from_ansi(text))
        except Exception:
            out.write(text)

    def _log_separator(self) -> None:
        out = self.query_one("#out", RichLog)
        out.write(Text.from_markup("[dim]" + ("-" * 60) + "[/]"))

    # ─── actions ─────────────────────────────────────────────────────────────
    def action_clear_log(self) -> None:
        self.query_one("#out", RichLog).clear()

    def action_kill_running(self) -> None:
        proc = self._current_proc
        if not proc or proc.poll() is not None:
            self._log_line("[info] no running command to cancel")
            return
        self._log_line("> Ctrl+K  sending SIGTERM")
        try:
            proc.send_signal(signal.SIGTERM)
        except OSError as exc:
            self._log_line(f"[error] SIGTERM failed: {exc}")
            return
        # escalate if still alive after 3s
        for _ in range(30):
            time.sleep(0.1)
            if proc.poll() is not None:
                return
        self._log_line("> still alive after 3s  sending SIGKILL")
        try:
            proc.kill()
        except OSError as exc:
            self._log_line(f"[error] SIGKILL failed: {exc}")

    def action_cycle_theme(self) -> None:
        self._theme_index = (self._theme_index + 1) % len(R42_THEMES)
        self.theme = R42_THEMES[self._theme_index].name
        self._save_state()
        self._log_line(f"> theme: {R42_THEMES[self._theme_index].name}")

    def action_toggle_description(self) -> None:
        self._show_descriptions = not self._show_descriptions
        self._apply_cmd_pane_width()
        # remember the highlight so we can restore it after the rebuild
        try:
            cmd_list = self.query_one("#cmd-list", OptionList)
            prev_highlight = cmd_list.highlighted
            cmd_list.clear_options()
        except Exception:
            prev_highlight = None
        self._populate_commands()
        if prev_highlight is not None:
            try:
                cmd_list = self.query_one("#cmd-list", OptionList)
                if 0 <= prev_highlight < cmd_list.option_count:
                    cmd_list.highlighted = prev_highlight
            except Exception:
                pass
        self._save_state()
        self._log_line(f"> descriptions: {'on' if self._show_descriptions else 'off'}")

    def _apply_cmd_pane_width(self) -> None:
        try:
            pane = self.query_one("#cmd-pane")
            pane.styles.width = (
                self.CMD_PANE_WIDTH_WIDE if self._show_descriptions
                else self.CMD_PANE_WIDTH_COMPACT
            )
        except Exception:
            pass

    # ─── state persistence ───────────────────────────────────────────────────
    def _save_state(self) -> None:
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            try:
                cmd_list = self.query_one("#cmd-list", OptionList)
                cursor = cmd_list.highlighted or 0
            except Exception:
                cursor = 0
            STATE_PATH.write_text(json.dumps({
                "cursor_index": cursor,
                "theme_index": self._theme_index,
                "show_descriptions": self._show_descriptions,
            }))
        except (OSError, ValueError):
            pass

    def _load_state(self) -> None:
        try:
            st = json.loads(STATE_PATH.read_text())
        except (OSError, ValueError):
            return
        try:
            ti = int(st.get("theme_index", 0))
            if 0 <= ti < len(R42_THEMES):
                self._theme_index = ti
        except (ValueError, TypeError):
            pass
        if "show_descriptions" in st:
            self._show_descriptions = bool(st.get("show_descriptions"))
        # cursor_index is restored AFTER _populate_commands runs in on_mount
        self._pending_cursor_index = st.get("cursor_index")


def main() -> int:
    app = ContextTUI()
    rc = app.run(inline=False)
    # textual returns whatever app.exit() received as return_code, or None
    if rc is None:
        return EXIT_QUIT
    if isinstance(rc, int):
        return rc
    return EXIT_QUIT


if __name__ == "__main__":
    sys.exit(main())
