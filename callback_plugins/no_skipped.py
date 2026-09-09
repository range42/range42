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

    def v2_runner_on_skipped(self, result):
        # attempt to overwrite the method to avoid printing skipped task.
        return

    def v2_runner_item_on_skipped(self, result):
        pass
