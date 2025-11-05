# range42
RANGE42 – modular cyber range platform for security training environments on Proxmox nodes.

## Architecture Overview
The RANGE42 platform consists of five integrated components:

1. **Deployer UI** (`pub/range42-deployer-ui/`) – Vue 3 + VueFlow visual designer for infrastructure design
2. **Backend API** (`pub/range42-backend-api/`) – FastAPI orchestration layer executing Ansible playbooks
3. **Proxmox Controller** (`pub/range42-ansible_roles-proxmox_controller/`) – Ansible role for Proxmox API/CLI interaction
4. **Catalog** (`pub/range42-catalog/`) – Reusable Ansible roles and Docker bundles (including CVE reproductions)
5. **Playbooks** (`pub/range42-playbooks/`) – Automation scenarios and reusable bundles

**Data Flow:** Deployer UI → Backend API → Ansible Playbooks → Proxmox Controller → Proxmox VE

## Repository Layout
- `pub/` – Active development code for all public components
- `priv/` – Reference documentation, architectural diagrams, and private assets (read-only)
- `pub/range42-playbooks/` – Ansible scenarios (demo_lab, forensics_lab, kunai_lab, misp_lab) and bundles
- `pub/range42-ansible_roles-proxmox_controller/` – Role that drives Proxmox via HTTPS API and CLI
- `pub/range42-catalog/` – Reusable content:
  - `02_ansible_layer/admin/roles/` – 22 Ansible roles (software installation, configuration, system checks)
  - `03_container_layer/docker/_ctf/cve/` – CVE reproductions organized by category (web, crypto, network, system)
- `pub/range42-backend-api/` – FastAPI server with Ansible runner integration
- `pub/range42-deployer-ui/` – Vue 3 SPA with VueFlow node-based canvas

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

### 1. Configure Inventory
Start from `pub/range42-playbooks/scenarios/demo_lab/inventory/off_cr_42.yml`. Update it with your node names and, if necessary, add `ansible_host`, `ansible_user`, or `ansible_ssh_private_key_file` entries for:
- `px-testing` – used for HTTPS API calls (connection often set to `local`)
- `px-testing-cli` – SSH access to the hypervisor for `qm disk import` operations
- `r42.*` hosts – logical names for the VMs that will be created; ensure your SSH configuration resolves these names (via `/etc/hosts`, DNS, or `~/.ssh/config` ProxyJump definitions)

**Inventory Groups:**
- `r42_admin` – Admin infrastructure VMs (Wazuh, Kong, Docker registry, deployer UI)
- `r42_admin_wazuh_clients` – Wazuh monitoring clients
- `r42_student_box_group` – Student workstations
- `r42_vuln_box_group` – Vulnerable training VMs
- `proxmox` – Proxmox hypervisor hosts

### 2. Create Vault File
Vault files store sensitive data (API credentials, SSH keys, passwords) encrypted with Ansible Vault.

```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab/secrets"
./vault.create.sh px-testing.cr42_tailscale.yml
```

**Suggested vault content** (adjust to your environment):
```yaml
---
# Proxmox API credentials
proxmox_api_host: "px-testing.example.com:8006"
proxmox_api_user: "api@pve"
proxmox_api_token_id: "ansible"
proxmox_api_token_secret: "SECRET"

# Default cloud-init credentials for cloned VMs
default_admin_vm_ci_user: "alice"
default_admin_vm_ci_password: "supersecret"
default_admin_vm_ci_ssh_key: |
  ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA....

# Local SSH hygiene
VAULT_operator_ssh_config_known_hosts: "/Users/steve/.ssh/known_hosts"

# Tailscale connectivity for admin/student/vuln groups
vault_tailscale_authkey: "tskey-auth-…"
tailscale_tags:
  - ranger

# Optional global SSH defaults if using ProxyJump
ansible_user: root
ansible_ssh_common_args: "-F /Users/steve/.ssh/config"
```

The playbooks import this file via `vars_files`, so any additional secrets (e.g., `tailscale_up_skip`, Wazuh passwords) can live here. Store the decryption password in a safe location, e.g. `/tmp/vault/vault_pass.txt`.

**Vault Management Scripts:**
```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab/secrets"
./vault.create.sh <vault-file>     # Create new vault
./vault.edit.sh <vault-file>       # Edit existing vault
./vault.view.sh <vault-file>       # View vault contents
./vault.changepwd.sh <vault-file>  # Change vault password
```

### 3. Review VM Definitions
Review the VM definitions under `pub/range42-playbooks/scenarios/demo_lab/02_admin_infrastructure/stage_00/*.yml`, `03_student_infrastructure/`, and `04_ctf_infrastructure/` to confirm the VM IDs, IPs, and tags align with your lab topology.

**Default Demo Lab Topology:**
- **Admin services:** `192.168.42.100–123` (VM IDs `1000–1023`)
  - Wazuh stack, Kong API Gateway, Docker registry, Deployer UI, EMP mockup
- **Student workstation:** `192.168.42.160` (VM ID `1400`)
- **Vulnerable boxes:** `192.168.42.170–174` (VM IDs `1700–1704`)
  - Docker-based CVE reproductions for training

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

## Available Scenarios
The `pub/range42-playbooks/scenarios/` directory contains multiple training environments:

### 1. demo_lab (Comprehensive)
Full cyber range with admin infrastructure, student workstations, and vulnerable VMs for CTF training.

### 2. forensics_lab
Specialized environment for digital forensics training.

### 3. kunai_lab
Linux security monitoring lab featuring Kunai (alternative to auditd) for detection and analysis.

### 4. misp_lab
Threat intelligence platform lab with MISP (Malware Information Sharing Platform).

Each scenario follows the same deployment pattern as demo_lab with its own inventory and vault configuration.

## Per-VM Management
Individual VM management scripts are available in `pub/range42-playbooks/scenarios/demo_lab/secrets/devkit/`:

```bash
cd "$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab/secrets/devkit"

# Individual VM operations
./r42-<vm-name>.install.sh    # Deploy specific VM
./r42-<vm-name>.delete.sh     # Delete specific VM
./r42-<vm-name>.snapshot.sh   # Create snapshot of VM
./r42-<vm-name>.revert.sh     # Revert VM to snapshot
```

These scripts are useful for:
- Testing individual VM deployments
- Iterative development of new infrastructure components
- Selective VM management without running full scenario playbooks

## Deployer UI (Web Interface)
The Vue 3 deployer provides a visual node-based canvas for infrastructure design.

### Setup and Run
```bash
cd "$RANGE42_ROOT/pub/range42-deployer-ui"
npm ci                    # Install dependencies
npm run dev              # Start development server (http://localhost:3000)
```

### Production Build
```bash
npm run build            # Build for production (output: dist/)
npm run preview          # Preview production build
```

### Testing
```bash
npm run test:unit        # Run Vitest unit tests
npm run test:e2e         # Run Playwright end-to-end tests
npm run test:e2e:ui      # Playwright UI mode
npx playwright install   # Install Playwright browsers (first time only)
```

### Features
- **VueFlow Canvas:** Drag-and-drop node-based infrastructure design
- **Node Status Indicators:**
  - Gray: Incomplete configuration
  - Orange: Ready to deploy
  - Red: Error state
  - Green: Successfully deployed
- **LocalStorage Persistence:** Projects saved locally (future: SQLite WASM)
- **i18n Support:** English (default), French available
- **Backend Integration:** Connects to FastAPI backend at `http://localhost:8000`

## Backend API Integration
The FastAPI backend orchestrates Ansible playbook execution and provides REST endpoints for infrastructure management.

### Setup and Run
```bash
cd "$RANGE42_ROOT/pub/range42-backend-api"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./start.sh   # Installs Ansible collections, exports env vars, launches uvicorn
```

The backend starts on `http://0.0.0.0:8000` with interactive documentation at:
- Swagger UI: `http://localhost:8000/docs/swagger`
- ReDoc: `http://localhost:8000/redoc`

### Required Environment Variables
The `start.sh` script sets these automatically, but for manual configuration:

```bash
export PROJECT_ROOT_DIR="$RANGE42_ROOT/pub/range42-backend-api"
export API_BACKEND_PUBLIC_PLAYBOOKS_DIR="$RANGE42_ROOT/pub/range42-playbooks"
export API_BACKEND_WWWAPP_PLAYBOOKS_DIR="$PROJECT_ROOT_DIR/playbooks"
export API_BACKEND_INVENTORY_DIR="$PROJECT_ROOT_DIR/inventory"
export API_BACKEND_VAULT_FILE="$RANGE42_ROOT/pub/range42-playbooks/scenarios/demo_lab/secrets/px-testing.cr42_tailscale.yml"
export VAULT_PASSWORD_FILE="/tmp/vault/vault_pass.txt"
```

### API Endpoints
Example endpoints (see Swagger docs for complete list):
- `GET /v0/admin/proxmox/vms/list` – List all VMs
- `POST /v0/admin/proxmox/vms/create` – Create new VM
- `POST /v0/admin/proxmox/vms/snapshot/create` – Create VM snapshot
- `POST /v0/admin/proxmox/vms/start` – Start VM
- `POST /v0/admin/proxmox/vms/stop` – Stop VM

### Testing API Endpoints
```bash
cd "$RANGE42_ROOT/pub/range42-backend-api/curl_utils"
# Use provided curl scripts or httpx commands to test endpoints
```

The backend expects the same inventory and vault files used by direct playbook execution.

## Catalog Components

### Ansible Roles (22 Available)
Located in `pub/range42-catalog/02_ansible_layer/admin/roles/`:

**Software Installation:**
- `software.install.tailscale` – Tailscale VPN client
- `software.install.wazuh*` – Wazuh components (agent, manager, indexer, dashboard, filebeat)
- `software.install.nodejs_app_systemd` – Node.js applications as systemd services
- `software.install.updates` – System package updates
- `software.install.warmup.*` – Basic packages, dotfiles, local bin setup

**Software Configuration:**
- `software.configure.docker-compose` – Docker Compose stack deployment
- `software.configure.firewalls` – Firewall rule management
- `software.configure.tailscale_disable_nftables` – Tailscale networking tweaks

**System Operations:**
- `systems.checks.overview` – System health checks
- `systems.configure.add_user` – User account management
- `service.reload.ntp` – NTP service management

**Utilities:**
- `ansible.utils` – Common utility tasks (wait for cloud-init, check SSH, delete Tailscale)

### CVE Catalog (Docker-based)
Located in `pub/range42-catalog/03_container_layer/docker/_ctf/cve/`:

**Organized by Category:**
- **crypto/** – Cryptographic vulnerabilities (OpenSSL CVEs)
  - CVE-2014-0160 (Heartbleed)
  - CVE-2022-0778 (Infinite loop in BN_mod_sqrt)

- **web/** – Web application vulnerabilities
  - Apache Tomcat CVEs
  - PHP vulnerabilities
  - Vite path traversal
  - PDF.js exploits

- **network/** – Network service vulnerabilities
  - OpenSSH CVEs
  - Erlang SSH vulnerabilities

- **system/** – System-level vulnerabilities
  - Sudo privilege escalation CVEs

**Each CVE Bundle Contains:**
- `Dockerfile` – Vulnerable container definition
- `compose.yml` – Docker Compose configuration
- `poc/meta.json` – CVE metadata (product, version, CVSS score, references)

**Adding New CVEs:**
Use the blank template at `pub/range42-catalog/03_container_layer/docker/_ctf/cve/blank_template/`

### Proxmox Controller Capabilities
The `pub/range42-ansible_roles-proxmox_controller/` role provides comprehensive Proxmox management:

**VM/LXC Lifecycle:**
- Create, delete, start, stop, pause, resume, clone
- List VMs with usage statistics
- Get/set configuration (CPU, RAM, CDROM, tags)

**Snapshot Management:**
- Create, revert, delete, list snapshots (VMs and LXC)

**Template Operations:**
- Create VM templates from cloud-init images
- Cloud-init configuration (user, password, SSH keys)

**Storage:**
- List ISOs and templates
- Download ISOs from URLs

**Networking:**
- Add/delete/list network interfaces on VMs and nodes
- Virtual network configuration

**Firewall:**
- Enable/disable at datacenter, node, and VM levels
- Manage iptables rules and aliases
- Default SSH rules

**Task Organization:**
Located in `tasks/include/` with subdirectories: `vm/`, `lxc/`, `snapshot/`, `firewall/`, `network/`, `storage/`, `templates/`, `cluster/`

## Security Context
RANGE42 is an **authorized security training platform** containing intentionally vulnerable configurations and CVE reproductions for **educational purposes only**.

The catalog includes:
- Misconfigured services for privilege escalation training
- Known CVE reproductions (containerized)
- Defensive security tooling (Wazuh monitoring, firewall configurations)

**All vulnerable components are:**
- Containerized for isolation
- Intended for controlled lab environments
- Used for defensive security training and CTF challenges
- Part of authorized security testing environments

**Do NOT deploy vulnerable components on production networks or internet-facing systems.**

## Troubleshooting Tips

### Common Issues
**Missing Role Errors:**
- Ensure `ANSIBLE_ROLES_PATH` includes both:
  - `pub/range42-ansible_roles-proxmox_controller/roles`
  - `pub/range42-catalog/02_ansible_layer/admin/roles`

**API 401/403 Responses:**
- Verify Proxmox token has required permissions (see "Configure Proxmox Access")
- Check token ID/secret stored in vault file
- Confirm API endpoint is reachable

**`qm disk import` Failures:**
- Confirm `px-testing-cli` inventory host points to hypervisor
- Verify `qemu-img` is installed on Proxmox node
- Check SSH access to hypervisor as privileged user

**Docker Bundle Deployment Issues:**
- Ensure control node can reach `RANGE42_INVENTORY__DOCKER__CTF` path
- Verify Docker is installed on target VMs
- Check Docker Compose version compatibility

**Vault Password Errors:**
- Verify vault password file exists and has correct password
- Check `VAULT_PASSWORD_FILE` environment variable is set
- Ensure vault file is properly encrypted

**SSH Connection Issues:**
- Clear old SSH fingerprints: `./demo_lab.reset.ssh_keys.sh`
- Verify ProxyJump configuration in `~/.ssh/config`
- Check VM cloud-init has completed before attempting SSH

## Quick Reference

### Full Stack Deployment (All Components)
```bash
# 1. Start Backend API
cd pub/range42-backend-api && ./start.sh

# 2. Start Deployer UI (separate terminal)
cd pub/range42-deployer-ui && npm run dev

# 3. Deploy Infrastructure (separate terminal)
cd pub/range42-playbooks/scenarios/demo_lab
ansible-playbook -i inventory/off_cr_42.yml demo_lab.yml \
  --vault-password-file /tmp/vault/vault_pass.txt
```

### Access Points
- **Deployer UI:** http://localhost:3000
- **Backend API Docs:** http://localhost:8000/docs/swagger
- **Deployed VMs:** Configured IPs in `192.168.42.0/24` range

### Project Structure
```
range42/
├── pub/                                    # Active development code
│   ├── range42-backend-api/               # FastAPI + Ansible runner
│   ├── range42-deployer-ui/               # Vue 3 + VueFlow UI
│   ├── range42-playbooks/                 # Scenarios and bundles
│   ├── range42-ansible_roles-proxmox_controller/  # Proxmox API role
│   └── range42-catalog/                   # Ansible roles + CVE containers
└── priv/                                   # Reference docs (read-only)
    └── range42-documentation-private-obsidian/  # Architectural diagrams
```

