from ansible.plugins.callback.default import CallbackModule as DefaultCallbackModule


class CallbackModule(DefaultCallbackModule):
    """
    from 'classic' callback  :: remove 'skipped' events. (to debug)

    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "no_skipped"
    CALLBACK_NEEDS_WHITELIST = False

    def v2_runner_on_skipped(self, result):
        # attempt to overwrite the methode to avoid printing skipped task.
        return
