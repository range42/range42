# range42 — Operations reference

Daily operations, `range42-context` reference, credentials, updating, troubleshooting, and advanced setup.

For first-time setup, see [GETTING_STARTED.md](GETTING_STARTED.md).

---

## Table of contents

- [Using range42-context](#using-range42-context)
  - [List configured contexts](#list-configured-contexts)
  - [Use a configured context](#use-a-configured-context)
  - [Show the current context](#show-the-current-context)
  - [Inventory](#inventory)
  - [Try a single catalog element](#try-a-single-catalog-element)
  - [SSH into deployed VMs](#ssh-into-deployed-vms)
  - [Initialise a new context](#initialise-a-new-context)
  - [Overwrite an existing configuration](#overwrite-an-existing-configuration)
  - [Deploy / undeploy](#deploy--undeploy)
  - [Reload SSH keys](#reload-ssh-keys)
  - [Full command list](#full-command-list)
- [Where credentials live](#where-credentials-live)
  - [Workspace layout](#workspace-layout)
  - [Where is the vault password](#where-is-the-vault-password)
  - [How to view the vault contents](#how-to-view-the-vault-contents)
  - [I lost my Proxmox root password](#i-lost-my-proxmox-root-password)
  - [I lost my SSH keys for the VMs](#i-lost-my-ssh-keys-for-the-vms)
  - [I want to back up everything](#i-want-to-back-up-everything)
- [Updating range42](#updating-range42)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Manual setup (advanced)](#manual-setup-advanced)
- [Extend the scenarios](#extend-the-scenarios)

---

## Using range42-context

`range42-context` is the daily-use tool. It manages workspaces, switches between
infrastructures and scenarios, deploys/cleans up VMs, and reloads SSH keys.

It's a **shell function** (zsh), sourced from `~/.zshrc`. So `range42-context use`
modifies the current shell - no need to restart, no need to spawn subshells.

### List configured contexts

> Lists all configured contexts (workspaces) on this deployer-cli, with the active one marked.

A workspace is a `codename + scenario` combination. After step 7 of the wizard, you have one.
After multiple `range42-context init` runs, you have several.

```
$ range42-context list

  ── available workspaces ──────────────────────────────────────
  ● [1]  mylab-blank_scenario_2_subnets       range42-context use mylab blank_scenario_2_subnets
  ○ [2]  mylab-demo_lab                       range42-context use mylab demo_lab
  ○ [3]  otherlab-blank_scenario_4_subnets    range42-context use otherlab blank_scenario_4_subnets
```

The active workspace is marked `●`. Inactive workspaces are `○`. The right
column shows the exact command to switch to that workspace.

### Use a configured context

> Switches your shell to a configured context. SSH config, vault password,
> environment variables and prompt are all updated.

```
$ range42-context use mylab demo_lab

  ── switching context ────────────────────────────────────────
   ✓  workspace        : mylab-demo_lab
   ✓  vault password   : ~/range42.config/mylab-demo_lab/secrets/vault_pass.txt
   ✓  ssh keys loaded  : 4 keys
   ✓  ssh include      : ~/.ssh/config_range42-mylab-demo_lab
   ✓  prompt updated   : [mylab/demo_lab]
```

After this, all `range42-context` commands operate on the new workspace.

### Show the current context

> Shows which context is currently active in your shell.

```
$ range42-context current
mylab-demo_lab
```

### Inventory

Lists all hosts the active workspace will deploy:

```
$ range42-context inventory

@all:
  |--@range42_infrastructure:
  |  |--@r42_admin:
  |  |  |--r42.admin-wazuh
  |  |  |--r42.admin-deployer-api-gateway
  |  |  |--r42.admin-deployer-api-backend
  |  |  |--r42.admin-deployer-ui
  |  |--@r42_admin_wazuh_clients:
  |  |  |--r42.admin-deployer-api-gateway
  |  |  |--r42.admin-deployer-api-backend
  |  |  |--r42.admin-deployer-ui
  |  |--@r42_vuln_box_group:
  |  |  |--r42.vuln-box-00
  |  |  |--r42.vuln-box-01
  |  |  |--r42.vuln-box-02
  |  |  |--r42.vuln-box-03
  |  |  |--r42.vuln-box-04
  |  |--@proxmox:
  |  |  |--mylab
  |  |--@proxmox_cli:
  |  |  |--mylab-cli
```

Useful for sanity-checking what would be deployed before running `deploy`.

### Try a single catalog element

For fast iteration on a single deployable element (Docker compose / Makefile)
from [range42-catalog](https://github.com/range42/range42-catalog) without
rebuilding a full lab, range42 ships a disposable-VM mode :

```bash
range42-context catalog-try-list                # browse available elements
range42-context catalog-try docker/_ctf/hello   # deploy + smoke-check one
```

`catalog-try` resolves the logical path, deploys the element on the
`catalog_try` VM, runs it, and smoke-checks it per the element's contract
(`catalog_try.yml` declaring L2 service / oneshot / L1 fallback). Each run
destroys + recreates the test VM, so iteration is fast and stateless. Admin
elements (Gitea, Mattermost, Nextcloud ...) are listed separately via
`catalog-try-list-admin`.

You can also bootstrap a fresh deployer-cli directly into this mode from your
laptop :

```bash
./range42-init.py --catalog-try docker/_ctf/hello
```

The wizard skips the scenario picker, forces `scenario=catalog_try`, and the
final banner suggests the right `range42-context catalog-try <path>` to run.

### SSH into deployed VMs

`range42-context use` configures **two** things at once:
- Ansible inventory (for `range42-context deploy`)
- SSH config (for `ssh <hostname>` directly)

So once a workspace is active, you can SSH into any deployed VM by name:

```
$ ssh r42.bs2-team-143-01
alice@bs2-team-143-01:~$

$ ssh r42.admin-wazuh
alice@admin-wazuh:~$
```

The hostnames are defined in the auto-generated SSH config:
`~/.ssh/config_range42-<codename>-<scenario>` (included from `~/.ssh/config`).

VMs are on isolated bridges (vmbr143, vmbr144, etc.) - your operator machine
has no direct route to them. SSH uses **ProxyJump** through the Proxmox host:

```
   ┌─────────────────┐         ┌──────────────────────┐         ┌───────────────────────┐
   │  your machine   │  ssh    │  Proxmox             │  ssh    │  bs2-team-143-01      │
   │  (operator)     │ ──────▶ │  user: jump_user     │ ──────▶ │  user: alice          │
   │                 │         │  on internet bridge  │         │  on internal vmbr143  │
   │  ssh key:       │         │                      │         │                       │
   │  jump_user key  │         │  (ProxyJump only,    │         │  ssh key:             │
   │  + alice key    │         │  no shell session)   │         │  alice key            │
   └─────────────────┘         └──────────────────────┘         └───────────────────────┘
```

Both keys are loaded into your ssh-agent by `range42-context use`. If they
disappear (after reboot), reload them:

```bash
range42-context ssh-reload
```

### Initialise a new context

Use the wizard to add a new scenario or a new Proxmox infrastructure:

```bash
range42-context init
```

This launches `range42-init.py` again. From there you can:

- **Add a scenario to an existing codename** → pick the codename in step 2,
  then change the scenario in step 6 (e.g., switch from `blank_scenario_2_subnets`
  to `demo_lab`)
- **Add a new infrastructure (codename)** → pick "new" in step 2,
  enter a different codename in step 3

After init completes, the new workspace appears in `range42-context list`.

```
$ range42-context list

  ── available workspaces ──────────────────────────────────────
  ● [1]  mylab-blank_scenario_2_subnets       range42-context use mylab blank_scenario_2_subnets
  ○ [2]  mylab-demo_lab                       range42-context use mylab demo_lab    ← new
```

### Overwrite an existing configuration

If you want to redo a configuration from scratch (wrong Proxmox address,
changed credentials, etc.) — re-run the wizard and pick the existing config
in step 2 instead of "new".

```bash
range42-context init
```

In step 2, you'll see all your configured contexts listed below `◆ new`.
Pick the one you want to overwrite — the wizard will pre-fill all the fields
from the existing config, so you only need to update what changed.

> ⚠️ Overwriting a configuration **does not destroy deployed VMs**. It only
> regenerates the local files (inventory, vault, SSH keys). If you also want
> to clean up the running VMs, run `range42-context delete` afterwards (or
> before, if the existing keys won't work anymore).

You can also use this flow to:
- Update the Proxmox API address after migrating the host
- Re-generate SSH keys / vault if they got corrupted
- Tweak which bridges have NAT enabled
- Change the deployer-cli IP / user

### Deploy / undeploy

```bash
range42-context deploy        # full deploy (templates + VMs + software)
range42-context deploy-vms    # fast redeploy (skip templates)
range42-context delete        # destroy everything + clean SSH known_hosts
range42-context delete-vms    # destroy VMs only (keep templates)
```

### Reload SSH keys

If your ssh-agent loses keys (after reboot, etc.):

```bash
range42-context ssh-reload
```

### Full command list

```
$ range42-context help

  usage: range42-context <command>

  workspace
    list                           list available workspaces
    current                        show active workspace
    use <codename> <scenario>      switch to a workspace
    status                         check workspace health
    init                           launch setup wizard

  navigation
    cd config                      go to workspace config directory
    cd scenario                    go to scenario playbooks directory
    cd secrets                     go to vault/secrets directory

  operations
    deploy                         run full scenario setup (templates + VMs)
    deploy-vms                     deploy VMs only (skip templates)
    delete                         delete all scenario VMs + templates
    delete-vms                     delete VMs only (keep templates)
    delete-everything              delete ALL VMs+templates across ALL scenarios
    reset                          delete + recreate all VMs
    ssh-reload                     reload SSH keys for active workspace

  lifecycle (all VMs of active scenario)
    start                          start all scenario VMs
    stop                           graceful shutdown of all scenario VMs
    stop-force                     force stop all scenario VMs
    pause                          pause all scenario VMs
    resume                         resume all paused scenario VMs
    snapshot [name]                snapshot all scenario VMs (auto-named if omitted)
    revert <name>                  revert all scenario VMs to a snapshot

  info
    inventory                      show ansible inventory tree
    passwords                      show generated credentials
    ssh <pattern>                  quick ssh to a VM by name
    debug                          toggle verbose output (show/hide skipped tasks)
    help                           show this help
```

---

## Where credentials live

range42 generates a lot of secrets at deploy time: SSH keys (4 of them), VM
passwords, the Wazuh password, the Proxmox API token. They all live under
your workspace, encrypted in an Ansible vault.

### Workspace layout

```
~/range42.config/<codename>-<scenario>/
├── secrets/
│   ├── default_vault.yml          ← encrypted vault (passwords, API token, etc.)
│   ├── vault_pass.txt             ← password to decrypt the vault (chmod 600)
│   ├── vault.view.sh              ← helper: view vault contents
│   ├── vault.edit.sh              ← helper: edit vault
│   ├── vault.create.sh            ← helper: create new vault
│   └── vault.changepwd.sh         ← helper: change vault password
├── ssh_keys/
│   ├── jump_keys/
│   │   ├── px.<codename>-<scenario>-ssh_cli.root         ← Proxmox root SSH key
│   │   └── px.<codename>-<scenario>-ssh_cli.jump_user    ← Proxmox jump user key
│   ├── backend_keys/
│   │   └── r42.<codename>-<scenario>-deployer-key_alice  ← admin user on VMs
│   └── student_keys/
│       └── r42.<codename>-<scenario>-student-key_bob     ← student user on VMs
├── inventory/
│   └── inventory_default.yml      ← ansible inventory (hosts + groups)
├── sourced_range42.sh             ← env vars sourced by range42-context use
└── scenario → ../../range42/range42-playbooks/scenarios/<scenario>/   ← symlink
```

### Where is the vault password

It's in the workspace, in plain text:

```
~/range42.config/<codename>-<scenario>/secrets/vault_pass.txt
```

This file has `chmod 600` and is owned by your user. It exists by design -
this is what allows `range42-context deploy` to run without prompting for the
vault password every time.

> ⚠️ This means **anyone with read access to your home directory can decrypt
> the vault**. Don't share `~/range42.config/` or back it up to insecure storage.

### How to view the vault contents

The vault contains generated VM passwords, the Wazuh password, the Proxmox API
token. To inspect them:

```bash
cd ~/range42.config/<codename>-<scenario>/secrets/
./vault.view.sh default_vault.yml
```

This wraps `ansible-vault view` and uses `vault_pass.txt` automatically.

To edit:

```bash
./vault.edit.sh default_vault.yml
```

Opens the vault in `$EDITOR`, encrypts on save.

### I lost my Proxmox root password

Run `cat default_vault.yml.example` is not it - the example is a template.

If you generated passwords during the wizard, the actual password is **inside
the vault**. View it:

```bash
./vault.view.sh default_vault.yml | grep -i password
```

If the wizard didn't generate it (you provided your own), it's not stored
anywhere by range42 - only the SSH root key was installed on Proxmox.

### I lost my SSH keys for the VMs

The keys live in `~/range42.config/<codename>-<scenario>/ssh_keys/`. As long as
you have this directory, you have everything.

If `range42-context use` complains about missing keys, run:

```bash
range42-context ssh-reload
```

If the keys themselves are physically deleted, the simplest recovery is to
redeploy:

```bash
range42-context delete
range42-context deploy   # regenerates SSH keys + vault, recreates Proxmox config
```

This is destructive - your VMs will be recreated from scratch.

### I want to back up everything

Tar the workspace directory — it contains everything needed to restore the deployment
on another machine (inventory, SSH keys, vault, vault password):

```bash
tar czf <codename>-<scenario>.r42.tar.gz \
    ~/range42.config/<codename>-<scenario>/
```

Store this tarball somewhere safe (encrypted disk, password manager attachment, etc.).

To restore on another machine: extract the tarball to `~/range42.config/`, then:

```bash
range42-context use <codename> <scenario>
```

---

## Updating range42

range42 lives in 5 git repos. To update everything to latest:

```bash
range42-context init     # easiest - the wizard pulls all 5 repos before showing the menu
```

Or manually:

```bash
for repo in range42 range42-playbooks range42-catalog \
            range42-ansible_roles-proxmox_controller \
            range42-ansible_roles-debug-devkit; do
  echo "=== $repo ==="
  cd ~/range42/$repo && git pull
done
```

After updating, you may want to redeploy to apply role/playbook changes:

```bash
range42-context delete-vms      # keeps templates
range42-context deploy-vms      # redeploy with new code (~5 min)
```

If a role under `~/range42/range42/roles/` changed (e.g., `deployer.bootstrap`),
run the full `site.yml` again via `range42-context init` to rebuild the
deployer-cli config.

---

## Troubleshooting

### The fast way - use range42-context

Most issues with stale state (failed deploy, partial cleanup, IP/key conflicts)
can be fixed by tearing down and redeploying. After `range42-context use <codename> <scenario>`:

```bash
# full reset (deletes templates + VMs + SSH known_hosts, then redeploys)
range42-context delete
range42-context deploy

# faster reset (keeps templates, recreates VMs only)
range42-context delete-vms
range42-context deploy-vms
```

This handles 90% of issues automatically - start here before deep-diving.

### What's happening behind the scenes

If you want to understand what's actually breaking before running `delete`:

**Wizard fails on preflight**
Missing local dependencies. Install the apt packages shown by the wizard.
The wizard checks: `ansible`, `ssh-keygen`, `ssh-agent`, `sshpass`, `git`, `keychain`, `zsh`,
plus Ansible collections `community.crypto` and `community.general`.

**Proxmox check fails**
The wizard couldn't reach `https://<address>:8006`. Verify manually with
`curl -k https://<address>:8006`. Common causes: wrong IP, firewall, Proxmox not running.

**Deploy fails on `vm_create` "already exists"**
Templates (vm_id 9211-9248) exist from a previous deploy. The proxmox controller
auto-skips them - just re-run. If the failure persists, run `range42-context delete`
to remove leftover state.

**SSH "REMOTE HOST IDENTIFICATION HAS CHANGED"**
The IP was previously used by a different VM with a different SSH host key.
The `delete` and `delete-vms` commands handle this automatically. To reset
known_hosts without redeploying:

```bash
~/range42/range42-playbooks/scenarios/blank_scenario_2_subnets/blank_scenario_2_subnets.reset.ssh_keys.sh
```

**Deploy fails on `chattr` errors during SSH key generation**
Already fixed in current version. Pull latest from range42 repo. The fix removes
`attributes: ""` from `openssh_keypair` which was failing on virtio/qcow2 disks.

**Vault corrupted or unable to decrypt**
The simplest recovery is to redeploy the VMs (the vault itself is regenerated
during deploy, and the SSH keys it references are also regenerated):

```bash
range42-context delete-vms
range42-context deploy-vms
```

This keeps the Proxmox templates (no need to re-download cloud images) but
recreates everything else, including a fresh vault.

If the vault is intact but you can't view it, check `vault_pass.txt` exists in
the same `secrets/` directory and is readable.

**Wazuh / admin VMs**
`blank_scenario_2_subnets` supports the admin infrastructure (wazuh server +
deployer platform on `vmbr142`). It's currently **disabled by default** because
not fully tested. To enable, edit `scenarios/blank_scenario_2_subnets/main.yml`
and uncomment the `01_admin_infrastructure/_main.yml` import.

---

## Project structure

The `range42` repo is laid out as follows:

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
├── roles/                    — 12 modular roles
└── config/                   — generated credentials (not committed)
```

The 12 roles:

| Role | Purpose |
|------|---------|
| `configuration.validate` | preflight variable checks |
| `credentials.generate` | SSH keypair generation |
| `credentials.vault` | vault creation and encryption |
| `proxmox.init` | Proxmox locale, NTP, IP forwarding, network bridges, NAT |
| `proxmox.jump-user` | creates the `jump_user` Linux account on Proxmox |
| `proxmox.api-token` | creates `range42_api` PAM user + API token |
| `deployer.bootstrap` | installs system packages, dotfiles, zsh, `range42-context` |
| `deployer.repos` | clones all 5 range42 git repos |
| `workspace.init` | creates workspace directory structure |
| `workspace.credentials` | uploads SSH keys + vault to deployer-cli |
| `workspace.ssh-config` | generates `~/.ssh/config` + per-workspace SSH host entries |
| `workspace.symlinks` | creates `secrets` and `scenario` symlinks in workspace |

The other 4 repos (`range42-playbooks`, `range42-catalog`,
`range42-ansible_roles-proxmox_controller`, `range42-ansible_roles-debug-devkit`)
are cloned by the wizard onto the deployer-cli during deploy. You don't
need them on your operator machine.

---

## Manual setup (advanced)

The wizard (`python3 range42-init.py`, covered in [GETTING_STARTED.md](GETTING_STARTED.md))
is the recommended path. The manual flow below exists for users who want
to script the setup, integrate it into their own tooling, or understand
exactly what gets executed.

It runs the same 3 playbooks the wizard runs, in the same order, against an
inventory you write by hand from the `inventories/example/` template.

```bash
# 1. Copy the template inventory
cp -r inventories/example inventories/my-infra

# 2. Edit the 3 files below with your settings:
#    - inventories/my-infra/hosts.yml                            (Proxmox + deployer-cli connection)
#    - inventories/my-infra/group_vars/all/vars.yml              (infrastructure settings)
#    - inventories/my-infra/group_vars/demo_lab/vars.yml         (scenario settings)

# 3. Generate credentials (SSH keys, vault, passwords) - runs locally
ansible-playbook playbooks/01_generate_credentials.yml \
  -i inventories/my-infra/hosts.yml \
  -e @inventories/my-infra/group_vars/demo_lab/vars.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab

# 4. Configure Proxmox (root key install, jump_user, API token, bridges, NAT)
ansible-playbook playbooks/02_configure_proxmox.yml \
  -i inventories/my-infra/hosts.yml \
  -e @inventories/my-infra/group_vars/demo_lab/vars.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab

# 5. Deploy the deployer-cli (packages, repos, workspace, SSH config, range42-context)
ansible-playbook playbooks/03_deploy_deployer_cli.yml \
  -i inventories/my-infra/hosts.yml \
  -e @inventories/my-infra/group_vars/demo_lab/vars.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab \
  --vault-password-file ./config/my-infra-demo_lab/secrets/vault_pass.txt

# 6. On the deployer-cli, use the workspace
range42-context use my-infra demo_lab
range42-context status
range42-context deploy
```

Note on `-e @...vars.yml`: this loads the scenario's group_vars as extra vars.
Without it, Ansible silently ignores `inventories/<cn>/group_vars/<scenario>/vars.yml`
because no inventory group matches the scenario name, and role defaults would win.

Or run all three at once via `site.yml`:

```bash
ansible-playbook site.yml \
  -i inventories/my-infra/hosts.yml \
  -e @inventories/my-infra/group_vars/demo_lab/vars.yml \
  -e INFRASTRUCTURE_SCENARIO=demo_lab \
  --vault-password-file ./config/my-infra-demo_lab/secrets/vault_pass.txt
```

---

## Extend the scenarios

All deployable scenarios live in [range42-playbooks/scenarios](https://github.com/range42/range42-playbooks/tree/main/scenarios) — the list will grow over time.

The reusable building blocks (CVEs, misconfigured services, product setups, Ansible roles) live in the [range42-catalog](https://github.com/range42/range42-catalog) repository.

**Want a specific product, CVE or misconfiguration added?** Open an issue on the [range42-catalog](https://github.com/range42/range42-catalog/issues) repo — we centralise catalog requests there.

**Found a bug or have a feature request for range42 itself?** Open an issue on the [range42](https://github.com/range42/range42/issues) repo (anything not related to the catalog goes here).

We'll prioritise as fast as we can.
