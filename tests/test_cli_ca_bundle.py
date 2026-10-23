"""Verified native API and public downloads share a private, temporary trust bundle."""
import datetime
import http.server
import json
import os
import shlex
import ssl
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'roles/deployer.bootstrap/files/range42-context.sh'


def certificate(directory, name):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .sign(key, hashes.SHA256()))
    ca, private = directory / (name + '.pem'), directory / (name + '.key')
    ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    private.chmod(0o600)
    return ca, private


@pytest.fixture
def tls_roots(tmp_path):
    servers = []
    values = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.reads += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'verified fixture')

        def log_message(self, *_):
            pass

    for name in ('public', 'native', 'unknown'):
        ca, private = certificate(tmp_path, name)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.reads = 0
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(ca, private)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        values.append({'ca': ca, 'url': 'https://localhost:' + str(server.server_port), 'server': server})
    yield values
    for server, thread in servers:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def environment(tmp_path, roots):
    config = tmp_path / 'ansible.cfg'
    config.write_text('[defaults]\nstdout_callback=default\nhost_key_checking=True\n')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('ANSIBLE_', 'RANGE42_')) and key not in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE')}
    env.update(RANGE42_QUIET='1', ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR='1',
               RANGE42_PROXMOX_CA_FILE=str(roots[1]['ca']), SSL_CERT_FILE=str(roots[0]['ca']),
               REQUESTS_CA_BUNDLE=str(roots[0]['ca']), TEST_REPORT=str(tmp_path / 'report.json'))
    return env


def reporter(tmp_path, exit_code=0):
    path = tmp_path / 'report.py'
    path.write_text('import json,os,ssl,stat,sys\nfrom pathlib import Path\n'
        'p=Path(os.environ["SSL_CERT_FILE"]);s=p.stat()\n'
        'value={"bundle":str(p),"requests_bundle":os.environ.get("REQUESTS_CA_BUNDLE"),'
        '"mode":stat.S_IMODE(s.st_mode),"uid":s.st_uid,"nlink":s.st_nlink,'
        '"contains_private_key":b"PRIVATE KEY" in p.read_bytes(),'
        '"certificates":len(ssl.create_default_context(cafile=str(p)).get_ca_certs())}\n'
        'Path(os.environ["TEST_REPORT"]).write_text(json.dumps(value))\n'
        f'sys.exit({exit_code})\n')
    return path


def scoped(env, argv, shell):
    command = f'''source {shlex.quote(str(SCRIPT))}
_r42_catalog_try_with_verified_api {' '.join(shlex.quote(str(value)) for value in argv)}
result=$?
printf 'RESTORED_SSL=%s\\n' "$SSL_CERT_FILE"
printf 'RESTORED_REQUESTS=%s\\n' "$REQUESTS_CA_BUNDLE"
exit $result
'''
    return subprocess.run([shell, '-c', command], env=env, capture_output=True, text=True, timeout=30, check=False)


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
def test_actual_ansible_uri_verifies_public_and_native_roots_but_refuses_unknown(tmp_path, tls_roots, shell):
    env = environment(tmp_path, tls_roots)
    report = reporter(tmp_path)
    playbook = tmp_path / 'tls.yml'
    playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
        'vars': {'ansible_python_interpreter': sys.executable}, 'tasks': [
            {'ansible.builtin.uri': {'url': '{{ item }}', 'validate_certs': True},
             'loop': [item['url'] for item in tls_roots], 'register': 'verified', 'failed_when': False},
            {'ansible.builtin.assert': {'that': ['verified.results[0].status == 200',
                'verified.results[1].status == 200', 'verified.results[2].status == -1']}},
            {'ansible.builtin.command': {'argv': [sys.executable, str(report)]}, 'changed_when': False}]}]))
    result = scoped(env, ['ansible-playbook', '-i', 'localhost,', str(playbook)], shell)
    assert result.returncode == 0, result.stdout + result.stderr
    assert [item['server'].reads for item in tls_roots] == [1, 1, 0]
    proof = json.loads(Path(env['TEST_REPORT']).read_text())
    assert proof['mode'] == 0o600 and proof['uid'] == os.getuid() and proof['nlink'] == 1
    assert proof['bundle'] == proof['requests_bundle']
    assert proof['certificates'] > 2  # Existing public system roots remain present.
    assert proof['contains_private_key'] is False
    assert not Path(proof['bundle']).exists()
    assert f"RESTORED_SSL={env['SSL_CERT_FILE']}\n" in result.stdout
    assert f"RESTORED_REQUESTS={env['REQUESTS_CA_BUNDLE']}\n" in result.stdout


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
@pytest.mark.parametrize('exit_code', [0, 7])
def test_private_ca_bundle_is_removed_on_success_and_command_failure(tmp_path, tls_roots, shell, exit_code):
    env = environment(tmp_path, tls_roots)
    result = scoped(env, [sys.executable, str(reporter(tmp_path, exit_code))], shell)
    assert result.returncode == exit_code, result.stdout + result.stderr
    proof = json.loads(Path(env['TEST_REPORT']).read_text())
    assert proof['mode'] == 0o600
    assert proof['bundle'] not in (env['SSL_CERT_FILE'], env['RANGE42_PROXMOX_CA_FILE'])
    assert not Path(proof['bundle']).exists()
    assert tls_roots[0]['ca'].is_file() and tls_roots[1]['ca'].is_file()
    assert f"RESTORED_SSL={env['SSL_CERT_FILE']}\n" in result.stdout


def test_invalid_selected_ca_fails_before_child_and_keeps_diagnostic_fixed(tmp_path, tls_roots):
    env = environment(tmp_path, tls_roots)
    tls_roots[1]['ca'].write_text('synthetic-private-parser-value\n')
    result = scoped(env, [sys.executable, str(reporter(tmp_path))], 'zsh')
    assert result.returncode != 0
    assert not Path(env['TEST_REPORT']).exists()
    assert 'synthetic-private-parser-value' not in result.stdout + result.stderr


@pytest.mark.parametrize('shell', ['bash', 'zsh'])
def test_terminated_child_scope_also_removes_private_bundle(tmp_path, tls_roots, shell):
    env = environment(tmp_path, tls_roots)
    child = reporter(tmp_path)
    child.write_text(child.read_text().replace('sys.exit(0)',
        'import signal,time\nos.kill(os.getppid(),signal.SIGTERM)\ntime.sleep(0.1)\nsys.exit(0)'))
    result = scoped(env, [sys.executable, str(child)], shell)
    assert result.returncode == 143, result.stdout + result.stderr
    proof = json.loads(Path(env['TEST_REPORT']).read_text())
    assert not Path(proof['bundle']).exists()
    assert f"RESTORED_SSL={env['SSL_CERT_FILE']}\n" in result.stdout
