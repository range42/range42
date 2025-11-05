# range42
RANGE42 – main playbook workspace for standing up a RANGE42 cyber range on Proxmox nodes.

## Repository Layout
- `pub/` – working copies of the public components (playbooks, catalog roles, backend API, deployer UI, etc.).
- `priv/` – reference material and private assets; treat these directories as read-only unless coordinating with range ops.
- `pub/range42-playbooks/` – Ansible scenarios and bundles used to build full environments.
- `pub/range42-ansible_roles-proxmox_controller/` – role that drives Proxmox via the HTTPS API and CLI.
- `pub/range42-catalog/` – reusable Ansible and Docker content consumed by the scenarios.

## Prerequisites
### Control Node
- Python 3.11+ and Ansible 2.15+.
- `ssh`, `jq`, `rsync`, and access to your Proxmox host.
- Ability to install Ansible Galaxy collections locally (`ansible-galaxy collection install ...`).

### Proxmox Cluster
- Proxmox VE 8 with `qm`, `qemu-img`, and `curl` available on the hypervisor.
- LVM storage named `local-lvm` plus ISO storage `local` (used by the playbooks).
- A bridge such as `vmbr0` providing the `192.168.42.0/24` network (the demo lab assigns static addresses in this range).
- An API token with permissions on the node you will target (sample node name: `px-testing`).

## Configure Proxmox Access
1. In the Proxmox UI create (or reuse) a service account, e.g. `api@pve`, and generate an API token (Permissions → `Datacenter.Audit`, `VM.Allocate`, `VM.Config.All`, `Sys.Modify`, and `Access.CloudInit` at the datacenter level are sufficient for the shipped playbooks).
2. Record the API endpoint `<proxmox-host>:8006`, token name, and secret; these values are injected via an Ansible vault file.
3. Ensure you can SSH to the hypervisor as `root` (or another privileged account) because template import tasks call `qm` and `qemu-img`.
4. If you reach the Proxmox API through an SSH tunnel or VPN, adjust the inventory so `px-testing` resolves to the API endpoint you actually hit (the sample inventory uses `127.0.0.1:18007` for a forwarded port).

## Prepare the Workspace
```bash
export RANGE42_ROOT=/Users/steve/GoogleDrive/code/range42
export RANGE42_GITDIR__ROOT_DIR="$RANGE42_ROOT/pub"                       # contains range42-deployer-ui, range42-emp-mockup, …
export RANGE42_INVENTORY__DOCKER__CTF="$RANGE42_ROOT/pub/range42-catalog/03_container_layer/docker/_ctf"
export ANSIBLE_ROLES_PATH="$RANGE42_ROOT/pub/range42-ansible_roles-proxmox_controller/roles:$RANGE42_ROOT/pub/range42-catalog/02_ansible_layer/admin/roles"
export ANSIBLE_COLLECTIONS_PATHS="$HOME/.ansible/collections:/usr/share/ansible/collections"
```

If your clones live elsewhere adjust `RANGE42_GITDIR__ROOT_DIR` and `RANGE42_INVENTORY__DOCKER__CTF` accordingly; the playbooks read these variables when they sync the UI code or Docker bundles.

### Python / Ansible Environment
```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab"
./_activate.sh            # creates and activates a venv under ~/ansible_fix
# shell now shows the virtualenv prompt
ansible-galaxy collection install community.general ansible.posix ansible.windows
```
The `_activate.sh` script mitigates Paramiko/cryptography issues on Ubuntu 24.04; source it before running playbooks.

## Inventory and Vault Files
1. Start from `pub/range42-playbooks/scenarios/demo_lab/inventory/off_cr_42.yml`. Update it with your node names and, if necessary, add `ansible_host`, `ansible_user`, or `ansible_ssh_private_key_file` entries for:
   - `px-testing` – used for HTTPS API calls (connection often set to `local`).
   - `px-testing-cli` – SSH access to the hypervisor for `qm disk import` operations.
   - `r42.*` hosts – logical names for the VMs that will be created; ensure your SSH configuration resolves these names (via `/etc/hosts`, DNS, or `~/.ssh/config` ProxyJump definitions).
2. Create the vault file consumed by every play:
   ```bash
   cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab/secrets"
   ./vault.create.sh px-testing.cr42_tailscale.yml
   ```
   Suggested content (adjust to your environment):
   ```yaml
   ---
   proxmox_api_host: "px-testing.example.com:8006"
   proxmox_api_user: "api@pve"
   proxmox_api_token_id: "ansible"
   proxmox_api_token_secret: "SECRET"

   # Default cloud-init credentials for the cloned machines
   default_admin_vm_ci_user: "alice"
   default_admin_vm_ci_password: "supersecret"
   default_admin_vm_ci_ssh_key: |
     ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA....

   # Local SSH hygiene
   VAULT_operator_ssh_config_known_hosts: "/Users/steve/.ssh/known_hosts"

   # Tailscale connectivity for the admin/student/vuln groups
   vault_tailscale_authkey: "tskey-auth-…"
   tailscale_tags:
     - ranger

   # Optional global SSH defaults if you rely on ProxyJump aliases
   ansible_user: root
   ansible_ssh_common_args: "-F /Users/steve/.ssh/config"
   ```
   The playbooks import this file via `vars_files`, so any additional secrets (e.g., `tailscale_up_skip`, Wazuh passwords) can live beside the values above. Store the decryption password in a safe location, e.g. `/tmp/vault/vault_pass.txt`.

3. Review the VM definitions under `pub/range42-playbooks/scenarios/demo_lab/02_admin_infrastructure/stage_00/*.yml`, `03_student_infrastructure/`, and `04_ctf_infrastructure/` to confirm the VM IDs, IPs, and tags align with your lab topology. The shipped demo lab expects:
   - Admin services on `192.168.42.100–123` (`vm_id` 1000–1023).
   - Student workstation `192.168.42.160` (`vm_id` 1400).
   - Vulnerable boxes `192.168.42.170–174` (`vm_id` 1700–1704).
   Update the `global_vm_*` variables inside those playbooks if you need different addressing.

## Deploy the Demo Lab
```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab"
# Optional: clear stale known_hosts entries
./demo_lab.reset.setup.sh

# Run the full scenario
ANSIBLE_STDOUT_CALLBACK=skippy \
ansible-playbook -i inventory/off_cr_42.yml demo_lab.yml \
  --vault-password-file /tmp/vault/vault_pass.txt
```

Execution order (`demo_lab.yml`) downloads cloud images, converts them into templates, clones admin/student/vuln VMs, applies catalog roles (packages, Tailscale, Wazuh, Docker bundles), and deploys the vulnerable services listed under `04_ctf_infrastructure/stage_01/*.yml`.

Expected outcomes:
- `template-vm-*` templates created on the Proxmox node (`vm_id` 9901–9932).
- Admin services online (Wazuh stack, API gateway, deployer UI, EMP mockups).
- A student workstation and multiple vulnerable nodes with Docker-based CVE reproductions sourced from `range42-catalog/03_container_layer/docker/_ctf`.

## Reset / Tear-down
To remove everything the demo lab created:
```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab"
./demo_lab.reset.setup.sh
```
The script stops and deletes VMs matching the admin/student/vuln naming scheme and prunes their SSH fingerprints.

## Backend API Integration (Optional)
Once the manual playbook run works, you can drive the same automation through the FastAPI backend:
```bash
cd "$RANGE42_ROOT/pub/range42-backend-api"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./start.sh   # exports API_BACKEND_* env vars and launches uvicorn
```
The backend expects the same inventory, vault file, and environment variables (`PROJECT_ROOT_DIR`, `API_BACKEND_PUBLIC_PLAYBOOKS_DIR`, etc.). Use the scripts under `pub/range42-backend-api/curl_utils/` to hit endpoints such as `/v0/admin/proxmox/vms/list` for automated deployments.

## Troubleshooting Tips
- Missing role errors usually mean `ANSIBLE_ROLES_PATH` is not set to include `range42-ansible_roles-proxmox_controller/roles` and `range42-catalog/02_ansible_layer/admin/roles`.
- API 401/403 responses indicate the Proxmox token lacks privileges; verify the user and token ID/secret stored in `px-testing.cr42_tailscale.yml`.
- If `qm disk import` fails, confirm `px-testing-cli` points at the hypervisor and that `qemu-img` is installed.
- Docker bundles assume the control node can reach the catalog directory specified by `RANGE42_INVENTORY__DOCKER__CTF`.

