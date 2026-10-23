"""Exercise ordinary context/use and catalog dispatch against reviewed lifecycle R."""
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'roles/deployer.bootstrap/files/range42-context.sh'


def fixture(tmp_path, *, failed_delete=False, caller_ca=None):
    reviewed = os.environ.get('RANGE42_REVIEWED_PLAYBOOKS')
    if not reviewed:
        pytest.skip('Set RANGE42_REVIEWED_PLAYBOOKS to the qualified R lifecycle checkout')
    home = tmp_path / 'home'
    checkout = home / 'range42'
    workspace = home / 'range42.config/lab-catalog_try'
    scenario = checkout / 'range42-playbooks/scenarios/catalog_try'
    shutil.copytree(Path(reviewed) / 'scenarios/catalog_try', scenario)
    for directory in (home / '.ssh', workspace / 'secrets', checkout / 'range42',
                      checkout / 'range42-ansible_roles-debug-devkit', tmp_path / 'bin', tmp_path / 'element'):
        directory.mkdir(parents=True, exist_ok=True)
    (home / '.ssh').chmod(0o700)
    (workspace / 'scenario').symlink_to(scenario)
    (workspace / 'sourced_range42.sh').write_text(f'export RANGE42_GITDIR__ROOT_DIR="{checkout}"\n')
    (workspace / 'secrets/vault_pass.txt').write_text('synthetic-fixture-only\n')
    (home / '.zshrc').write_text('')
    (home / '.ssh/config').write_text('Host r42.catalog-try-vm-docker\n HostName 192.168.142.250\n'
                                    ' GlobalKnownHostsFile /dev/null\n')
    shutil.copyfile(ROOT / 'ansible.cfg', checkout / 'range42/ansible.cfg')
    key = tmp_path / 'fixture-key'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
    public = ' '.join(key.with_suffix('.pub').read_text().split()[:2])
    pins = home / '.ssh/known_hosts'
    pins.write_text(''.join(host + ' ' + public + '\n' for host in
                           ('10.77.32.18', '192.168.142.250', '192.0.2.77')))
    pins.chmod(0o600)
    calls = tmp_path / 'calls.jsonl'
    state = tmp_path / 'state'
    state.write_text('0')
    program = f'''#!{sys.executable}
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
with open(os.environ['TEST_CALLS'],'a') as out:
 out.write(json.dumps({{'name':name,'argv':sys.argv[1:],'pins':Path(os.environ['TEST_PINS']).read_text(),
 'ca':os.environ.get('RANGE42_PROXMOX_CA_FILE'),'config':os.environ.get('ANSIBLE_CONFIG')}})+'\\n')
if name=='proxmox_vm.list.to.jsons.sh':
 p=Path(os.environ['TEST_STATE']);n=int(p.read_text());p.write_text(str(n+1))
 if n==0:print(json.dumps({{'vm_id':1250,'vm_name':'catalog-try-vm-docker','template':0}}))
 print(json.dumps({{'vm_id':9221,'vm_name':'template','template':1}}))
elif name!='ansible-playbook':
 sys.stdin.read()
 if name=='proxmox_vm.vm_id.delete.to.jsons.sh' and os.environ['TEST_DELETE_FAILED']=='1':sys.exit(17)
'''
    for name in ('proxmox_vm.list.to.jsons.sh', 'proxmox_vm.vm_id.stop_force.to.jsons.sh',
                 'proxmox_vm.vm_id.delete.to.jsons.sh', 'ansible-playbook'):
        target = tmp_path / 'bin' / name
        target.write_text(program)
        target.chmod(0o700)
    env = {key: value for key, value in os.environ.items() if not key.startswith(('ANSIBLE_', 'RANGE42_'))}
    env.update(HOME=str(home), PATH=str(tmp_path / 'bin') + os.pathsep + os.environ['PATH'],
               RANGE42_QUIET='1', RANGE42_CONFIG_BASE_DIR=str(home / 'range42.config'),
               RANGE42_CONTEXT_REPO_LINKS_MANAGED='NO', RANGE42_ANSIBLE_ROLES__INVENTORY_DIR='/fixture',
               ANSIBLE_SSH_COMMON_ARGS='-F ' + shlex.quote(str(home / '.ssh/config')),
               TEST_CALLS=str(calls), TEST_STATE=str(state), TEST_PINS=str(pins),
               TEST_DELETE_FAILED='1' if failed_delete else '0')
    if caller_ca is not None:
        env['RANGE42_PROXMOX_CA_FILE'] = caller_ca
    return {'env': env, 'pins': pins, 'calls': calls, 'element': tmp_path / 'element', 'checkout': checkout}


@pytest.mark.parametrize('failed_delete', [True, False])
@pytest.mark.parametrize('caller_ca', [None, '/fixture/operator-qualified-ca.pem'])
def test_ordinary_catalog_use_deletion_and_enrollment_preserve_strict_trust(tmp_path, failed_delete, caller_ca):
    f = fixture(tmp_path, failed_delete=failed_delete, caller_ca=caller_ca)
    before = f['pins'].read_text()
    command = f'''source {shlex.quote(str(SCRIPT))}
_r42_ssh_reload() {{ return 0; }}
_r42_status() {{ return 0; }}
_r42_catalog_resolve_path() {{ print -r -- {shlex.quote(str(f['element']))}; }}
_r42_catalog_try_yml_get() {{ print -r -- "$3"; }}
range42-context use lab catalog_try || exit $?
cp "$TEST_PINS" "$TEST_PINS.after-use"
range42-context catalog-try fixture
result=$?
print -r -- "RESTORED_CA=${{RANGE42_PROXMOX_CA_FILE-UNSET}}"
exit $result
'''
    result = subprocess.run(['zsh', '-f', '-c', command], input='y\n', env=f['env'],
                            capture_output=True, text=True, timeout=20, check=False)
    assert f['pins'].with_name('known_hosts.after-use').read_text() == before
    calls = [json.loads(line) for line in f['calls'].read_text().splitlines()]
    assert all(call['pins'] == before for call in calls if call['name'] != 'ansible-playbook')
    assert (result.returncode != 0) is failed_delete, result.stdout + result.stderr
    assert f"RESTORED_CA={caller_ca if caller_ca is not None else 'UNSET'}" in result.stdout
    ansible = [call for call in calls if call['name'] == 'ansible-playbook']
    if failed_delete:
        assert f['pins'].read_text() == before
        assert not ansible
    else:
        assert f['pins'].read_text() == ''.join(line for line in before.splitlines(keepends=True)
                                              if not line.startswith('192.168.142.250 '))
        assert len(ansible) == 2
        assert ansible[0]['argv'][-4:] == ['-e', 'range42_guest_hostkey_from_pve_agent=true',
                                          '-e', 'proxmox_api_validate_certs=true']
        assert ansible[0]['ca'] == caller_ca
        assert ansible[0]['config'] == str(f['checkout'] / 'range42/ansible.cfg')


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
@pytest.mark.parametrize('state', ['qualified', 'caller', 'missing', 'symlink', 'nonroot', 'writable', 'hardlinked'])
@pytest.mark.parametrize('operation', ['guest', 'template'])
def test_catalog_ca_scope_requires_secure_native_file_and_preserves_caller(tmp_path, shell, state, operation):
    ca = tmp_path / 'qualified-ca.pem'
    if state != 'missing':
        ca.write_text('synthetic public CA fixture\n')
        ca.chmod(0o644)
    if state == 'symlink':
        original = ca.with_name('real-ca.pem')
        ca.rename(original)
        ca.symlink_to(original)
    metadata = {'nonroot': '1000:644:1', 'writable': '0:664:1', 'hardlinked': '0:644:2'}.get(state, '0:644:1')
    script = tmp_path / 'context.sh'
    script.write_text(SCRIPT.read_text().replace('/etc/range42-workshop-pve-ca.pem', str(ca)))
    env = {key: value for key, value in os.environ.items() if key != 'RANGE42_PROXMOX_CA_FILE'}
    if state == 'caller':
        env['RANGE42_PROXMOX_CA_FILE'] = '/operator/qualified-ca.pem'
    dispatch = '_r42_catalog_try_deploy_vms' if operation == 'guest' else '_r42_catalog_try_with_verified_api _r42_deploy_vms'
    command = f'''source {shlex.quote(str(script))}
stat() {{ printf '%s\\n' {shlex.quote(metadata)}; }}
_r42_deploy_vms() {{ printf 'SELECTED=%s\\n' "${{RANGE42_PROXMOX_CA_FILE-UNSET}}"; printf 'ARG=%s\\n' "$@"; }}
{dispatch} || exit $?
printf 'RESTORED=%s\\n' "${{RANGE42_PROXMOX_CA_FILE-UNSET}}"
'''
    result = subprocess.run([shell, '-c', command], env=env, capture_output=True, text=True, timeout=5, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    expected = str(ca) if state == 'qualified' else '/operator/qualified-ca.pem' if state == 'caller' else 'UNSET'
    assert f'SELECTED={expected}\n' in result.stdout
    assert f"RESTORED={'/operator/qualified-ca.pem' if state == 'caller' else 'UNSET'}\n" in result.stdout
    assert result.stdout.count('ARG=range42_guest_hostkey_from_pve_agent=true\n') == (1 if operation == 'guest' else 0)
    assert result.stdout.count('ARG=proxmox_api_validate_certs=true\n') == 1


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
@pytest.mark.parametrize('wrapper_exists', [True, False])
@pytest.mark.parametrize('caller_ca', [None, '/operator/qualified-ca.pem'])
def test_templates_only_dispatch_preserves_pins_context_and_literal_arguments(tmp_path, shell, wrapper_exists, caller_ca):
    f = fixture(tmp_path, caller_ca=caller_ca)
    scenario = f['checkout'] / 'range42-playbooks/scenarios/catalog_try'
    wrapper = scenario / 'catalog_try.setup_templates_only.sh'
    if wrapper_exists:
        wrapper.write_text('#!/bin/bash\nansible-playbook ./main_templates_only.yml "$@"\n')
    else:
        wrapper.unlink(missing_ok=True)
    before = f['pins'].read_bytes()
    command = f'''source {shlex.quote(str(SCRIPT))}
_r42_ssh_reload() {{ return 0; }}
_r42_status() {{ return 0; }}
range42-context use lab catalog_try || exit $?
range42-context deploy-templates --start-at-task 'fixed task; no interpretation' -e proxmox_api_validate_certs=false
'''
    result = subprocess.run([shell, '-c', command], env=f['env'], capture_output=True,
                            text=True, timeout=10, check=False)
    assert (result.returncode == 0) is wrapper_exists, result.stdout + result.stderr
    assert f['pins'].read_bytes() == before
    calls = [json.loads(line) for line in f['calls'].read_text().splitlines()] if f['calls'].exists() else []
    if wrapper_exists:
        assert len(calls) == 1 and calls[0]['name'] == 'ansible-playbook'
        assert calls[0]['argv'] == ['./main_templates_only.yml', '--start-at-task',
                                     'fixed task; no interpretation', '-e', 'proxmox_api_validate_certs=false',
                                     '-e', 'proxmox_api_validate_certs=true']
        assert calls[0]['config'] == str(f['checkout'] / 'range42/ansible.cfg')
        assert calls[0]['ca'] == caller_ca
    else:
        assert 'catalog_try.setup_templates_only.sh' in result.stdout + result.stderr
        assert not calls


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
def test_other_scenario_template_dispatch_does_not_rewrite_its_arguments_or_configuration(tmp_path, shell):
    f = fixture(tmp_path, caller_ca='/operator/qualified-ca.pem')
    scenario = tmp_path / 'other_scenario'
    scenario.mkdir()
    (scenario / 'other_scenario.setup_templates_only.sh').write_text(
        '#!/bin/bash\nansible-playbook ./main_templates_only.yml "$@"\n')
    link = Path(f['env']['HOME']) / 'range42.config/lab-catalog_try/scenario'
    link.unlink()
    link.symlink_to(scenario)
    f['env']['RANGE42_ACTIVE_CONFIG_DIR'] = str(link.parent)
    f['env']['ANSIBLE_CONFIG'] = '/operator/strict.cfg'
    before = f['pins'].read_bytes()
    command = f'source {shlex.quote(str(SCRIPT))}\nrange42-context deploy-templates -e operator_feature=true'
    result = subprocess.run([shell, '-c', command],
                            env=f['env'], capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f['pins'].read_bytes() == before
    calls = [json.loads(line) for line in f['calls'].read_text().splitlines()]
    assert len(calls) == 1
    assert calls[0]['argv'] == ['./main_templates_only.yml', '-e', 'operator_feature=true']
    assert calls[0]['ca'] == '/operator/qualified-ca.pem'
    assert calls[0]['config'] == '/operator/strict.cfg'
