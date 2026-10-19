import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def test_no_skipped_callback_keeps_failure_messages_visible_on_installed_ansible(tmp_path):
    play=tmp_path/'fail.yml';play.write_text('''- hosts: localhost
  gather_facts: false
  tasks:
    - ansible.builtin.fail:
        msg: CALLBACK_FAILURE_MUST_REMAIN_VISIBLE
''')
    env={k:v for k,v in os.environ.items() if not k.startswith('ANSIBLE_')}
    env.update(ANSIBLE_CALLBACK_PLUGINS=str(ROOT/'callback_plugins'),ANSIBLE_STDOUT_CALLBACK='no_skipped')
    result=subprocess.run(['ansible-playbook','-c','local','-i','localhost,',str(play)],env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert 'CALLBACK_FAILURE_MUST_REMAIN_VISIBLE' in result.stdout
    assert "unexpected keyword argument 'hostvars'" not in result.stdout+result.stderr


def test_callback_supports_base_versions_without_hostvars(monkeypatch):
    import importlib.util
    from ansible.plugins.callback.default import CallbackModule as DefaultCallback
    monkeypatch.setattr(DefaultCallback,'get_option',lambda self,option:'visible')
    spec=importlib.util.spec_from_file_location('no_skipped_fixture',ROOT/'callback_plugins/no_skipped.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.CallbackModule().get_option('display_ok_hosts')=='visible'
