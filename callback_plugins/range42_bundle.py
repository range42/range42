# range42_bundle : the stdout callback of the bundles launched from the shell by range42-context.
#
# It prints what a bundle SAYS and every failure, nothing else : the messages of the debug tasks,
# the success message of the asserts (the verdicts), and in full every failed task, failed loop
# item, unreachable host and play without host. No task list, no ok/changed lines, no skipped.
# The fact of a failure is never hidden, the exit code of ansible-playbook carries it ; only the
# noise is. Whatever this callback does not recognise in a failure is dumped as json, so a new
# kind of error is loud rather than silent.
#
# WHAT THE BUNDLE SAYS IS AT THE LEVEL OF THE PLAY, NOT OF A ROLE. The proxmox_controller role
# prints a debug of its whole api answer after nearly every action, ninety three of them and none
# under a condition : left in, they bury the four sentences the bundle wrote for the operator. So a
# message coming from a role is never printed here, while a FAILURE coming from a role always is,
# wherever it happens. Someone who wants the payloads wants the whole log, and asks for it with
# range42-context debug-on, which does not use this callback at all.
#
# Enabled per run by the runner, never in ansible.cfg :
#   ANSIBLE_STDOUT_CALLBACK=range42_bundle ANSIBLE_CALLBACK_PLUGINS=<this directory> ansible-playbook ...
#
# The glyphs and colours are the ones of range42-context (step, check, fail), so a bundle's words
# read like the lines of the command that launched it.

from __future__ import annotations

import json

from ansible.plugins.callback import CallbackBase

DOCUMENTATION = """
    name: range42_bundle
    type: stdout
    short_description: prints what a bundle says and every failure, nothing else
    description:
      - Meant for the bundles that range42-context launches from the shell.
      - Prints the messages of the debug tasks of the play, the success message of its asserts,
        and every failed task, failed loop item, unreachable host or play without host, in full.
      - Never prints the messages the roles print ; a failure in a role is always printed.
      - Prints no task list, no ok or changed line, nothing for skipped tasks.
"""

STEP = "    \033[34m➜\033[0m "
CHECK = "    \033[32m✓\033[0m "
FAIL = "    \033[31m✗\033[0m "
INDENT = "        "
NOISE_KEYS = ("_ansible_no_log", "_ansible_verbose_always", "_ansible_verbose_override", "invocation", "changed", "failed", "skipped", "skip_reason", "results", "item", "ansible_loop_var", "ansible_loop", "_ansible_item_label", "_ansible_ignore_errors", "_ansible_parsed", "warnings", "deprecations", "exception")


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "range42_bundle"
    CALLBACK_NEEDS_ENABLED = False

    # ---- helpers ------------------------------------------------------------------------------

    @staticmethod
    def _action(result):
        action = getattr(result._task, "action", "") or ""
        return action.split(".")[-1]

    @staticmethod
    def _name(result):
        return (result._task.get_name() or "").strip()

    @staticmethod
    def _from_role(result):
        """A task of a role, as opposed to a task the bundle itself wrote in its play."""
        return getattr(result._task, "_role", None) is not None

    @staticmethod
    def _label(result):
        label = result._result.get("_ansible_item_label", result._result.get("item"))
        if label is None:
            return ""
        return " [item: %s]" % (label if isinstance(label, str) else json.dumps(label, ensure_ascii=False))

    def _lines(self, value):
        """A message as lines of text : a string, a list of strings, or anything else as json."""
        if isinstance(value, str):
            return value.splitlines() or [""]
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            out = []
            for v in value:
                out.extend(v.splitlines() or [""])
            return out
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).splitlines()

    def _say(self, text):
        self._display.display(text)

    def _say_block(self, text):
        """A block opens with a blank line : a run is read at a glance, not parsed."""
        self._display.display("")
        self._display.display(text)

    def _say_indented(self, value):
        for line in self._lines(value):
            self._say(INDENT + line)

    def _say_debug(self, result):
        r = result._result
        self._say_block(STEP + self._name(result) + self._label(result))
        if "msg" in r:
            self._say_indented(r["msg"])
            return
        payload = {k: v for k, v in r.items() if k not in NOISE_KEYS}
        for key in sorted(payload):
            self._say(INDENT + "%s = %s" % (key, json.dumps(payload[key], ensure_ascii=False)))

    def _say_assert_ok(self, result):
        msg = result._result.get("msg")
        if isinstance(msg, str) and msg and msg != "All assertions passed":
            self._say_block(CHECK + msg)
        else:
            self._say_block(CHECK + self._name(result))

    def _say_failure(self, result, suffix=""):
        r = result._result
        self._say_block(FAIL + self._name(result) + self._label(result) + suffix)
        if r.get("msg"):
            self._say_indented(r["msg"])
        if r.get("assertion") is not None:
            self._say(INDENT + "assertion : %s" % json.dumps(r["assertion"], ensure_ascii=False))
        for key in ("stderr", "stdout", "module_stderr", "module_stdout", "reason"):
            if r.get(key):
                self._say(INDENT + "%s :" % key)
                self._say_indented(r[key])
        if r.get("rc") is not None:
            self._say(INDENT + "rc : %s" % r["rc"])
        if not r.get("msg") and not any(r.get(k) for k in ("stderr", "stdout", "module_stderr", "module_stdout", "reason")):
            payload = {k: v for k, v in r.items() if k not in NOISE_KEYS}
            if payload:
                self._say_indented(payload)

    # ---- what the bundle says -------------------------------------------------------------------

    def v2_runner_on_ok(self, result):
        r = result._result
        if "results" in r and isinstance(r["results"], list):
            return  # a loop : each item was already handled
        if self._from_role(result):
            return  # the role own api dumps : range42-context debug-on shows the whole log instead
        action = self._action(result)
        if action == "debug":
            self._say_debug(result)
        elif action == "assert":
            self._say_assert_ok(result)

    def v2_runner_item_on_ok(self, result):
        if self._from_role(result):
            return
        action = self._action(result)
        if action == "debug":
            self._say_debug(result)
        elif action == "assert":
            self._say_assert_ok(result)

    # ---- every failure, in full -----------------------------------------------------------------

    def v2_runner_on_failed(self, result, ignore_errors=False):
        r = result._result
        if "results" in r and isinstance(r["results"], list):
            return  # a loop : each failed item was already printed
        self._say_failure(result, " (ignored, the run goes on)" if ignore_errors else "")

    def v2_runner_item_on_failed(self, result):
        ignored = result._result.get("_ansible_ignore_errors") or getattr(result._task, "ignore_errors", False)
        self._say_failure(result, " (ignored, the run goes on)" if ignored else "")

    def v2_runner_on_unreachable(self, result):
        self._say_block(FAIL + "%s unreachable : %s" % (result._host.get_name(), result._result.get("msg", "")))

    def v2_playbook_on_no_hosts_matched(self):
        self._say_block(FAIL + "no host matched the play : nothing was run")

    def v2_playbook_on_no_hosts_remaining(self):
        self._say_block(FAIL + "no host remaining : the play stops here")

    def v2_playbook_on_stats(self, stats):
        ## one blank line before the list, not one per host : the recap stays a block
        first = True
        for host in sorted(stats.processed.keys()):
            s = stats.summarize(host)
            if s["failures"] or s["unreachable"]:
                line = FAIL + "%s : failed=%s unreachable=%s" % (host, s["failures"], s["unreachable"])
                self._say_block(line) if first else self._say(line)
                first = False

    # ---- silence ----------------------------------------------------------------------------------

    def v2_playbook_on_start(self, playbook):
        pass

    def v2_playbook_on_play_start(self, play):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        pass

    def v2_playbook_on_handler_task_start(self, task):
        pass

    def v2_playbook_on_include(self, included_file):
        pass

    def v2_runner_on_skipped(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_runner_retry(self, result):
        pass

    def v2_on_file_diff(self, result):
        pass
