# RANGE42

**RANGE42** is a modular cyber range platform for building and deploying realistic cyber training infrastructures on-premises.

New to range42? See the [GLOSSARY](GLOSSARY.md) for terminology (codename, scenario, workspace, jump host, etc.)

# QUICK START

## Supported platforms

The wizard has been tested on:
- Ubuntu Desktop LTS (24.04)
- Ubuntu Server LTS (24.04)
- Debian 13.x LTS (netinstall)

## Option A — Setup wizard (recommended)

The wizard guides you through the configuration and can deploy automatically:

```bash
python3 range42-init.py
```

![range42-init wizard](screenshots/0002.png)

Requires: `pip install --user textual` (do NOT use `apt install python3-textual`, version too old).

It will:
1. Check prerequisites (ansible, ssh-keygen, sshpass, collections)
2. Ask for your Proxmox address, node name, and a codename
3. Create an inventory with your settings
4. Optionally run the full deployment (credentials, Proxmox setup, deployer-cli)

After the wizard, on the deployer-cli:

```bash
range42-context use <codename> <scenario>
range42-context status
range42-context deploy
```

To add another infrastructure later: `range42-context init`
(only available after the first deployment has set up the tools)

## Option B — Manual setup

### Prerequisites

- A Proxmox hypervisor with SSH root access
- Ansible installed on your local machine
- `community.crypto` and `community.general` Ansible collections
- `sshpass` (for automatic SSH key installation)

### 1. Configure your inventory

```bash
cp -r inventories/example inventories/my-infra
```

Edit the following files with your infrastructure settings:
- `inventories/my-infra/hosts.yml` — Proxmox address and deployer-cli connection
- `inventories/my-infra/group_vars/all/vars.yml` — infrastructure settings
- `inventories/my-infra/group_vars/demo_lab/vars.yml` — scenario settings

### 2. Generate credentials

```bash
ansible-playbook playbooks/01_generate_credentials.yml \
  -i inventories/my-infra/hosts.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab
```

### 3. Configure Proxmox

```bash
ansible-playbook playbooks/02_configure_proxmox.yml \
  -i inventories/my-infra/hosts.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab
```

### 4. Deploy the deployer-cli

```bash
ansible-playbook playbooks/03_deploy_deployer_cli.yml \
  -i inventories/my-infra/hosts.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab \
  --vault-password-file ./config/my-infra-demo_lab/secrets/vault_pass.txt
```

### 5. Use the workspace

On the deployer-cli:

```bash
range42-context use my-infra demo_lab
range42-context status
range42-context deploy
```


# DAILY OPERATIONS

Once deployed, manage your lab with `range42-context`:

```bash
range42-context status              # check workspace health
range42-context deploy              # full deploy (templates + VMs)
range42-context deploy-vms          # fast redeploy (VMs only, skip templates)
range42-context delete-vms          # delete VMs (keep templates)
range42-context delete              # delete everything
range42-context reset               # delete + recreate

range42-context ssh wazuh           # quick SSH to a VM
range42-context inventory           # show inventory tree
range42-context passwords           # show credentials
range42-context cd scenario         # navigate to playbooks
range42-context help                # all commands
```

# PROJECT STRUCTURE

```
range42/
├── range42-init.py           — setup wizard (Python/Textual TUI)
├── ansible.cfg
├── site.yml                  — runs all 3 playbooks in sequence
├── playbooks/
│   ├── 01_generate_credentials.yml
│   ├── 02_configure_proxmox.yml
│   └── 03_deploy_deployer_cli.yml
├── inventories/
│   └── example/              — copy and customize for your infra
├── roles/                    — 11 modular roles
├── utils/                    — range42-context and range42-workspace
└── config/                   — generated credentials (not committed)
```

# WHAT IS RANGE42

RANGE42 provides two main capabilities:
- Deploy vulnerable and misconfigured hosts
- Include an extensible catalogue of ready-to-deploy CVEs, misconfigured services and product setup

In its recommended configuration, RANGE42 relies on:

- **Proxmox** — hypervisor for virtual machines (mandatory)
- **Ansible** — provisioning and orchestration (mandatory)
- **Docker / LXC** — containerized services and vulnerable stacks (recommended)
- **Wazuh** — security monitoring and detection (optional)
- **Firewalls / VPN** — network segmentation and access control (recommended)
- **Vue.js / FastAPI / Kong** — web UI and API layer (optional)

## Host groups

| Group | Purpose | Required |
|-------|---------|----------|
| **Vulnerable targets** | Core lab systems for attack and analysis | Yes |
| **Administration** | Monitoring, orchestration, supervision | No |
| **Student / Training** | Workstations for learners | No |

Only the vulnerable hosts group is required. Admin and student groups can be disabled to save resources.

## Deployer-cli

The deployer-cli is the machine that runs the Ansible playbooks and manages the lab.
We recommend a dedicated VM or laptop, not the Proxmox host itself.

# FOR WHO

- **Sysadmins** — practice securing vulnerable stacks and test hardening procedures
- **SOC analysts / blue teams** — validate detection rules, tune alerts, test incident response
- **Red teamers / researchers** — build exploit chains, study CVEs in controlled environments
- **Forensics teams** — reconstruct incidents, analyse compromised systems

# GLOSSARY

See [GLOSSARY.md](GLOSSARY.md) for all terminology: codename, scenario, workspace,
deployer-cli, jump host, vault, context, range42-context, host groups, inventory.

# AUTHORS

See AUTHORS file.
