# Ansible callback plugin that suppresses skipped-task output.
# Inherits everything from the default callback; only overrides the two
# "skipped" display methods. Failures are never affected.
#
# Enable in ansible.cfg:
#   [defaults]
#   stdout_callback = no_skipped
from ansible.plugins.callback.default import CallbackModule as DefaultCallbackModule


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
