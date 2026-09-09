# Ansible callback plugin that suppresses skipped-task output.
# Inherits everything from the default callback; only overrides the two
# "skipped" display methods. Failures are never affected.
#
# Enable in ansible.cfg:
#   [defaults]
#   stdout_callback = no_skipped
#
# THE DOCUMENTATION BLOCK BELOW IS NOT DOCUMENTATION, IT IS WHAT MAKES THE PLUGIN RUN.
# A stdout callback reads its own options through self.get_option(), and those options come
# from its DOCUMENTATION. Without the block, and without inheriting the fragments of the
# default callback it derives from, every dispatch that reads an option dies : recent Ansible
# answers each task with "Callback dispatch 'v2_playbook_on_task_start' failed for plugin
# 'no_skipped': 'display_skipped_hosts'" and prints NO task at all. Measured on ansible-core
# 2.21 : with the block, the output is the default one minus the skipped tasks, failed loop
# items and assert reasons included.
from ansible.plugins.callback.default import CallbackModule as DefaultCallbackModule

DOCUMENTATION = """
    name: no_skipped
    type: stdout
    short_description: the default output, without the skipped tasks
    description:
      - Everything the default callback prints, minus the lines of the skipped tasks.
      - Failures, the failed items of a loop included, are printed exactly as the default does.
    extends_documentation_fragment:
      - default_callback
      - result_format_callback
"""


class CallbackModule(DefaultCallbackModule):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "no_skipped"
    CALLBACK_NEEDS_WHITELIST = False
    CALLBACK_NEEDS_ENABLED = False

    # HIDING A SKIPPED TASK MEANS HIDING ITS BANNER TOO, AND ANSIBLE ALREADY KNOWS HOW.
    # The default callback prints the "TASK [...]" banner right away only while both of its
    # display options are on ; with display_skipped_hosts off it DEFERS the banner and prints it
    # from the result handlers, so a task every host skips prints nothing at all. Overriding the
    # skipped methods alone left the banner behind, and a role full of conditional includes then
    # showed a wall of empty banners. The option is forced here rather than asked for as a line in
    # ansible.cfg, so the whole behaviour of the toggle lives in the plugin the toggle enables.
    def get_option(self, option, hostvars=None):
        if option == "display_skipped_hosts":
            return False
        return super().get_option(option, hostvars=hostvars)

    # belt and braces : with the option off the default already prints nothing for these two,
    # and they keep the promise of the name even if the option ever comes back on.
    def v2_runner_on_skipped(self, result):
        return

    def v2_runner_item_on_skipped(self, result):
        return
