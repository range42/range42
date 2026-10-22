"""Native SSH detects dead sessions and retries only connection failures."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('relative', ['ansible.cfg', 'roles/deployer.bootstrap/templates/ansible.cfg.j2'])
def test_native_ssh_plugin_bounds_dead_sessions_without_changing_authentication(tmp_path, relative):
    config = tmp_path / 'ansible.cfg'
    config.write_text((ROOT / relative).read_text())
    code = '''import json
from ansible.plugins.loader import connection_loader
from ansible.playbook.play_context import PlayContext
p=connection_loader.get('ssh',PlayContext(),None)
p.set_options()
print(json.dumps({'args':p.get_option('ssh_args'),'retries':p.get_option('reconnection_retries'),'pipelining':p.get_option('pipelining')}))'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
        env={**os.environ, 'ANSIBLE_CONFIG': str(config)}, check=True)
    value = json.loads(result.stdout)
    effective = subprocess.run(['ssh', '-G', '-F', '/dev/null', *shlex.split(value['args']), 'guest.invalid'],
        capture_output=True, text=True, check=True)
    options = dict(line.split(' ', 1) for line in effective.stdout.splitlines())
    assert options['serveraliveinterval'] == '15'
    assert options['serveralivecountmax'] == '3'
    assert options['controlmaster'] == 'auto'
    assert options['controlpersist'] == '60'
    assert value['retries'] == 3
    assert value['pipelining'] is True
    assert 'stricthostkeychecking' not in value['args'].lower()
    assert 'identityfile' not in value['args'].lower()

@pytest.mark.parametrize('binary,results,expected_calls,raises', [
    ('ssh', [255, 255, 0], 3, False),
    ('ssh', [1], 1, False),
    ('sshpass', [5], 1, True),
])
def test_retries_are_transport_only_and_never_repeat_remote_application_errors(tmp_path, binary, results, expected_calls, raises):
    config = tmp_path / 'ansible.cfg'
    config.write_text((ROOT / 'ansible.cfg').read_text())
    code = '''import json
from ansible.plugins.loader import connection_loader
from ansible.playbook.play_context import PlayContext
from ansible.plugins.connection import ssh
p=connection_loader.get('ssh',PlayContext(),None);p.set_options()
ssh.time.sleep=lambda seconds:None
values=iter(RESULTS);calls=[]
@ssh._ssh_retry
def attempt(self, command):
 calls.append(command);return(next(values),b'',b'fixture transport or application result')
raised=False
try:attempt(p,[BINARY.encode()])
except Exception:raised=True
print(json.dumps({'calls':len(calls),'raised':raised}))'''.replace('RESULTS', repr(results)).replace('BINARY', repr(binary))
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
        env={**os.environ, 'ANSIBLE_CONFIG': str(config)}, check=True)
    assert json.loads(result.stdout) == {'calls': expected_calls, 'raised': raises}
