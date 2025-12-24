# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is the **deployment machine configurator** for the RANGE42 cyber range platform. It provisions and configures a deployment machine (jump host) used to manage the RANGE42 infrastructure. This machine acts as the central orchestration point for deploying and managing Proxmox-based cyber training environments.

**Purpose:**
- Configure a dedicated deployment/jump host for RANGE42 operations
- Generate Ansible inventories, vaults, and deployment playbooks from master configuration
- Set up development tools, SSH keys, git configuration, and runtime environment
- Deploy secrets, tarballs, and configuration files to the deployer machine

**Key Technologies:**
- **Automation:** Ansible (core configuration management)
- **Target Infrastructure:** Proxmox virtualization platform
- **Containerization:** Docker and LXC (for deployed services)
- **Monitoring:** Wazuh (optional security event monitoring)
- **Web Stack:** Vue.js frontend and Python/FastAPI backend (optional, deployed via this host)

## Repository Structure

```
.
├── prepare-infrastructure-workspace.sh    # Main entrypoint script
├── config/                                # Configuration and vault management
│   ├── config_remote-deployer-cli.MASTER_FILE.yml  # Master configuration file
│   ├── vault.create.sh                    # Create new Ansible vault
│   ├── vault.edit.sh                      # Edit existing vault
│   ├── vault.view.sh                      # View vault contents
│   └── vault.changepwd.sh                 # Change vault password
├── roles/
│   └── configure.deployer-cli/            # Main Ansible role
│       ├── tasks/                         # Task files (numbered sequence)
│       ├── templates/                     # Jinja2 templates for config files
│       ├── files/                         # Static files to deploy
│       └── defaults/                      # Default variables
├── utils/                                 # Utility scripts
│   ├── ssh-agent.start.sh                 # Start SSH agent
│   └── ssh-add.unload_all_keys.to.text.sh # Unload SSH keys
└── README.md                              # Project documentation
```

## Build, Test, and Development Commands

### Workspace Preparation

```bash
# Generate inventories, vaults, and deployment playbooks
./prepare-infrastructure-workspace.sh

# This script reads config/config_remote-deployer-cli.MASTER_FILE.yml and generates:
# - Ansible inventory files
# - Vault files for secrets
# - Host-specific deployment playbooks (deploy.<host>-<scenario>.yml)
# - Deployment wrapper scripts (deploy.<host>-<scenario>.sh)
```

### Vault Management

```bash
# Create a new Ansible vault
./config/vault.create.sh

# Edit an existing vault
./config/vault.edit.sh

# View vault contents (read-only)
./config/vault.view.sh

# Change vault password
./config/vault.changepwd.sh
```

### Role Execution

```bash
# Option 1: Use generated deployment script
./deploy.<host>-<scenario>.sh

# Option 2: Run Ansible playbook directly
ansible-playbook -i inventories/<host>.yml deploy.<host>-<scenario>.yml -K

# Option 3: Test with check mode (dry run)
ansible-playbook -i inventories/<host>.yml deploy.<host>-<scenario>.yml --check
```

### SSH Utilities

```bash
# Start SSH agent
./utils/ssh-agent.start.sh

# Unload all SSH keys to text format
./utils/ssh-add.unload_all_keys.to.text.sh
```

## Code Architecture

### Main Entrypoint Script

**`prepare-infrastructure-workspace.sh`**
- Reads master configuration from `config/config_remote-deployer-cli.MASTER_FILE.yml`
- Generates Ansible inventories for target deployment hosts
- Creates vault files for sensitive data (passwords, keys, tokens)
- Generates host-specific playbooks and wrapper scripts
- Validates configuration and sets up workspace structure

### Ansible Role: `configure.deployer-cli`

The core role that configures the deployment machine. Tasks are organized in numbered sequence files:

**Task Execution Order:**
1. **`00_dev_mode.yml`** - Development mode configuration (optional setup for testing)
2. **`01_packages.yml`** - Install required system packages (Python, Ansible, git, etc.)
3. **`02_shell.yml`** - Configure shell environment (bash/zsh, aliases, prompt)
4. **`03_dot_files.yml`** - Deploy dotfiles (.vimrc, .bashrc, .gitconfig, etc.)
5. **`04_ssh_client.yml`** - Configure SSH client and deploy keys
6. **`05_git.yml`** - Set up git configuration (user.name, user.email, aliases)
7. **`06_symlinks.yml`** - Create symbolic links for tools and scripts
8. **`07_01_deploy_inventory.yml`** - Deploy Ansible inventory files
9. **`07_02_deploy_ssh_keys.yml`** - Deploy SSH keys for infrastructure access
10. **`07_03_deploy_secrets_tarball.yml`** - Deploy encrypted secrets archive
11. **`07_04_deploy_sources_file.yml`** - Deploy APT sources configuration
12. **`08_clean_up.yml`** - Remove temporary files and clean workspace
13. **`09_dirty_fixes.yml`** - Apply workarounds for known issues
14. **`10_context_tools.yml`** - Install context-specific tools and utilities

**Role Structure:**
- `tasks/` - Numbered YAML files defining sequential tasks
- `templates/` - Jinja2 templates for generated configuration files (parameterized, no hardcoding)
- `files/` - Static files to be deployed as-is
- `defaults/main.yml` - Default variable values
- `main.yml` - Role entry point that includes all task files

### Configuration Pattern

**Master Configuration File:** `config/config_remote-deployer-cli.MASTER_FILE.yml`

This YAML file drives the entire deployment process and contains:
- Host definitions (deployment machine targets)
- User credentials and SSH keys
- Proxmox connection details
- Ansible vault passwords
- Environment-specific variables
- DEV_MODE flag for development environments

**Variable-Driven Design:**
- All configuration is defined in the master YAML
- Templates use Jinja2 variables to remain environment-agnostic
- No hardcoded values in templates or tasks
- Enables multi-environment support (dev, staging, production)

## Coding Conventions

### Shell Scripts (Bash)

- Use bash with safety flags (`set -euo pipefail` for strict error handling)
- Follow existing formatting style in the repository
- Keep scripts focused and single-purpose
- Add comments for non-obvious operations
- Use descriptive variable names

**Example:**
```bash
#!/usr/bin/env bash
set -euo pipefail

# Descriptive comment about what this does
VAULT_FILE="${VAULT_FILE:-config/vault.yml}"
ansible-vault edit "${VAULT_FILE}"
```

### Ansible YAML

- **Indentation:** 2 spaces (strict, no tabs)
- **Task naming:** Descriptive, action-oriented labels
- **Task file sequencing:** Numbered files in `tasks/` (e.g., `01_packages.yml`, `02_shell.yml`)
- **Templates:** Keep parameterized, avoid environment-specific hardcoding
- **Variables:** Define in `defaults/main.yml` or master config file

**Task Naming Convention:**
```yaml
- name: INSTALL - Essential deployment packages
  apt:
    name: "{{ deployer_packages }}"
    state: present
```

### Configuration Files

- Master config uses snake_case for keys
- YAML anchors and aliases encouraged for DRY configuration
- Comments should explain "why" not "what"
- Keep sensitive data in vaults, reference via variables

## Testing Guidelines

**Manual Validation Process:**

1. **Workspace Generation:**
   ```bash
   # Run workspace prep and verify no errors
   ./prepare-infrastructure-workspace.sh

   # Verify generated files exist
   ls -la inventories/
   ls -la deploy.*.yml
   ls -la deploy.*.sh
   ```

2. **Dry Run Testing:**
   ```bash
   # Test playbook with check mode (no actual changes)
   ansible-playbook -i inventories/<host>.yml deploy.<host>-<scenario>.yml --check
   ```

3. **Safe Environment Execution:**
   - Run generated playbook in a development/testing environment first
   - Verify each task completes successfully
   - Check deployed configuration files on target host
   - Validate SSH connectivity, git config, installed packages

4. **Vault Operations:**
   ```bash
   # Test vault can be created, edited, viewed
   ./config/vault.create.sh
   ./config/vault.edit.sh
   ./config/vault.view.sh
   ```

**No Automated Tests:**
- This repository has no CI/CD or automated test suite
- All validation is manual and operator-driven
- Test in isolated/safe environments before production use

## Development Workflow

### DEV_MODE Configuration

The project supports a `DEV_MODE` flag in the master configuration file:
- When enabled, alters setup process for development/testing
- May skip certain production-only steps
- Useful for iterative development on the deployment machine itself

### Making Changes

1. **Modify master config:** Edit `config/config_remote-deployer-cli.MASTER_FILE.yml`
2. **Update role tasks:** Modify numbered task files in `roles/configure.deployer-cli/tasks/`
3. **Update templates:** Edit Jinja2 templates in `roles/configure.deployer-cli/templates/`
4. **Test changes:** Run workspace prep and execute playbook in check mode
5. **Validate:** Deploy to test environment and verify results

### Adding New Deployment Targets

1. Add new host entry in master config file
2. Run `prepare-infrastructure-workspace.sh` to generate inventory
3. New `deploy.<host>-<scenario>.yml` and `.sh` files will be created
4. Test with check mode before actual deployment

## Commit Guidelines

Use imperative, component-prefixed subjects:
- `role: adjust deployer-cli git config`
- `scripts: tighten workspace prep validation`
- `config: add new host definition for staging`
- `templates: parameterize SSH key paths`
- `vault: add vault rotation script`

**Commit Body:**
- Mention affected configuration files or templates
- Document any breaking changes to master config schema
- Link related issues if applicable

## Pull Request Guidelines

- Link driving issue or feature request
- Document manual validation steps performed
- List affected hosts or environments
- Describe rollback procedure if deployment fails
- Mention any new variables added to master config
- Attach terminal output showing successful playbook execution
- Request review from infrastructure/operations team
- Wait for approval before merging

## Security Context

This deployment machine has elevated privileges and access to:
- **Proxmox API credentials** for full infrastructure control
- **SSH keys** for accessing all lab hosts
- **Ansible vaults** containing sensitive passwords and tokens
- **Network access** to management interfaces

**Security Considerations:**
- Vault files must remain encrypted at rest
- SSH keys should be passphrase-protected
- Deployment machine should be on isolated management network
- Access to this machine should be restricted and audited
- This is **authorized infrastructure management** for cyber training lab operations

**Intentional Vulnerabilities:**
This repository does NOT contain vulnerable code. It configures the secure deployment/jump host. The vulnerable systems are deployed BY this machine TO the RANGE42 lab environment for **authorized security testing and CTF challenges**.

## Integration with RANGE42 Ecosystem

This deployment machine serves as the orchestration hub for:
- **range42-backend-api** - FastAPI orchestration layer (optional)
- **range42-deployer-ui** - Vue 3 visual infrastructure designer (optional)
- **range42-catalog** - Ansible roles and Docker compose bundles
- **range42-playbooks** - Centralized playbooks for scenarios
- **range42-ansible_roles-proxmox_controller** - Proxmox API control role

The deployer machine is configured to:
- Clone and manage these repositories
- Execute playbooks against Proxmox infrastructure
- Provide a consistent development/operations environment
- Centralize credentials and access control
