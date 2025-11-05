# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RANGE42 is a modular cyber range platform for security training environments. The system orchestrates Proxmox-based infrastructure using a FastAPI backend, Vue 3 UI, Ansible automation, and Docker containerization.

**Architecture Flow:**
1. Deployer UI (Vue 3 + VueFlow) → visual infrastructure design
2. Backend API (FastAPI) → orchestration and playbook execution
3. Proxmox Controller (Ansible role) → Proxmox API interaction
4. Catalog (Ansible roles + Docker stacks) → deployable bundles
5. Playbooks → reusable automation scenarios

## Repository Structure

- `pub/` - Active development code
- `priv/` - Operations assets (read-only unless coordinated with ops)
- `pub/range42-backend-api/` - FastAPI orchestration layer
- `pub/range42-deployer-ui/` - Vue 3 visual designer
- `pub/range42-catalog/` - Ansible roles and Docker compose bundles
- `pub/range42-playbooks/` - Centralized playbooks for scenarios
- `pub/range42-ansible_roles-proxmox_controller/` - Proxmox API control role
- `pub/range42-api-definitions/` - OpenAPI specifications

## Build, Test, and Development Commands

### Backend API (FastAPI + Ansible)

```bash
# Setup environment
cd pub/range42-backend-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install community.general -p ~/.ansible/collections
ansible-galaxy collection install ansible.posix -p ~/.ansible/collections
ansible-galaxy collection install ansible.windows -p ~/.ansible/collections

# Start development server (requires environment variables)
./start.sh

# Validate catalog hooks
ansible-playbook -i inventory/sample generic.yml --check

# Format Python code
python -m black app/
# or
ruff format app/
```

**Required Environment Variables:**
- `PROJECT_ROOT_DIR` - Project root directory
- `API_BACKEND_PUBLIC_PLAYBOOKS_DIR` - Path to range42-playbooks
- `API_BACKEND_WWWAPP_PLAYBOOKS_DIR` - Backend playbooks directory
- `API_BACKEND_INVENTORY_DIR` - Ansible inventory directory
- `API_BACKEND_VAULT_FILE` - Ansible vault file path
- `VAULT_PASSWORD_FILE` or `VAULT_PASSWORD` - Vault authentication

### Deployer UI (Vue 3 + Vite)

```bash
# Setup
cd pub/range42-deployer-ui
npm ci

# Development server (hot reload)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Run tests
npm run test:unit              # Vitest unit tests
npm run test:e2e               # Playwright e2e tests
npm run test:e2e:ui            # Playwright UI mode

# Linting
npm run lint

# Install Playwright browsers (before first e2e run)
npx playwright install
```

### Ansible Roles and Playbooks

```bash
# Install role dependencies
ansible-galaxy install -r requirements.yml

# Run playbook with check mode
ansible-playbook -i inventory/px-testing playbooks/demo_lab.yml --check

# Lint playbooks
ansible-lint playbooks/*.yml
```

## Code Architecture

### Backend API (FastAPI)

**Structure:**
- `app/main.py` - FastAPI application entry point with CORS and vault initialization
- `app/routes/` - API router definitions organized by resource type
- `app/schemas/` - Pydantic models for request/response validation
- `app/utils/` - Helper utilities (inventory checks, text cleaning, VM ID resolution)
- `app/runner.py` - Ansible runner integration
- `playbooks/` - Backend-specific playbooks
- `inventory/` - Ansible inventory files

**Key Patterns:**
- Routes mirror catalog bundle structure (e.g., `bundles/core/proxmox/configure/default/vms/`)
- Schemas define data models for Proxmox operations (VMs, snapshots, networks, firewalls)
- Backend calls `range42-ansible_roles-proxmox_controller` role to interact with Proxmox API
- Results returned as JSON from Ansible playbook execution

### Deployer UI (Vue 3)

**Structure:**
- `src/components/` - Shared Vue components
- `src/stores/` - Pinia state management stores
- `src/composables/` - Reusable composition functions
- `src/composables/runnerCalls/bundle/` - Backend API call wrappers
- `src/locales/` - i18n translation files per language
- `src/router/` - Vue Router configuration
- `e2e/` - Playwright end-to-end tests

**Key Patterns:**
- VueFlow canvas for node-based infrastructure design
- Each node represents infrastructure component (VM, network, Docker container)
- Node status indicators: gray (incomplete), orange (ready), red (error), green (deployed)
- LocalStorage for project persistence (future: SQLite WASM)
- DaisyUI + Tailwind CSS for styling
- i18n with `vue-i18n` (English default, French provided)

### Catalog (Ansible + Docker)

**Structure:**
- `02_ansible_layer/` - Ansible roles for system configuration
- `03_container_layer/docker/_ctf/` - CVE and misconfiguration containers
- `04_gamification_layer/` - Themed templates for training scenarios

**Key Roles:**
- `software.install.*` - Software installation roles (Docker, Tailscale, Wazuh, etc.)
- `software.configure.*` - Configuration roles (firewalls, Docker compose, etc.)
- `systems.checks.*` - System validation roles
- `ansible.utils` - Utility tasks (wait for cloud-init, check SSH, delete Tailscale)

**CVE Catalog Pattern:**
Each CVE contains:
- `compose.yml` - Docker compose definition
- `poc/meta.json` - Metadata about the vulnerability
- Organized by category: `web/`, `network/`, `system/`, `crypto/`

### Playbooks (Ansible Scenarios)

**Structure:**
- `bundles/` - Reusable unit actions (create VMs, snapshots, install software)
- `scenarios/` - Complete infrastructure scenarios (demo_lab)

**Bundle Pattern:**
- `bundles/core/proxmox/configure/default/vms/` - VM lifecycle operations
- `bundles/core/linux/ubuntu/install/` - Ubuntu software installation
- Each bundle has `main.yml` entry point and may include multi-stage execution

### Proxmox Controller (Ansible Role)

**Capabilities:**
- VM/LXC lifecycle: create, delete, start, stop, pause, resume, clone
- Snapshots: create, revert, delete, list (for VMs and LXC)
- Templates: create VM templates, cloud-init configuration
- Storage: list ISOs/templates, download ISOs
- Networking: add/delete/list network interfaces (VMs and nodes)
- Firewall: enable/disable at DC/node/VM levels, manage iptables rules and aliases
- Configuration: get VM CPU/RAM/CDROM config, set tags

**Task Files:**
Located in `tasks/include/` organized by function:
- `vm/` - VM operations
- `lxc/` - LXC operations
- `snapshot/` - Snapshot management
- `firewall/` - Firewall configuration
- `network/` - Network management
- `storage/` - Storage operations
- `templates/` - Template and cloud-init

## Coding Conventions

### Python (Backend API)
- Follow PEP 8 with 4-space indentation
- Type hints on all public functions
- Routers in `app/routes/` named after catalog bundles
- Schemas use Pydantic models
- Format with `black` or `ruff format`

### Vue/TypeScript (Deployer UI)
- `<script setup>` composition API
- PascalCase for component filenames (e.g., `NodePalette.vue`)
- Colocated `*.spec.ts` tests in `__tests__/` directories
- Pinia stores in `src/stores/` with camelCase keys
- Follow i18n conventions in `docs/i18n-guide.md`

### Ansible (Playbooks/Roles)
- 2-space indentation for YAML
- Uppercase task labels mirroring role names: `RUN ACTION - role-name`
- Playbook structure: init → stage_00 → stage_01 → cleanup
- Role naming: `category.action.description` (e.g., `software.install.docker`)

## Testing Guidelines

### Backend API
- Document reproducible test steps in `curl_utils/` scripts
- Include `ansible-playbook --check` validation against `inventory/px-testing`
- Provide HTTPX or curl command examples for manual testing

### Deployer UI
- Unit tests: `npm run test:unit` (Vitest, located in `src/**/__tests__/`)
- E2E tests: `npm run test:e2e` (Playwright, located in `e2e/`)
- Include Playwright traces for regression reports
- Test i18n strings across all supported locales

## Commit Guidelines

Use imperative, component-prefixed subjects:
- `ui: add bundle selector component`
- `api: harden inventory loader validation`
- `catalog: add CVE-2025-12345 container`
- `playbooks: update demo_lab scenario`

Mention affected playbooks or bundles in commit body. Link driving issue if applicable.

## Pull Request Guidelines

- Link driving issue
- List manual verification commands (playbook runs, curl tests, UI workflows)
- Attach screenshots for UI changes or terminal output for API/playbook changes
- Document rollback steps for deployment scripts
- Request review from module owner (@deployer-ui, @backend-api, @catalog)
- Wait for one approval plus passing CI before merging

## Security Context

This is a cyber training platform containing intentionally vulnerable configurations and CVE reproductions for educational purposes. The catalog includes:
- Misconfigured services (FTP anonymous access, privilege escalation scenarios)
- Known CVE reproductions (OpenSSL, Sudo, web framework vulnerabilities)
- Defensive tooling (Wazuh monitoring, firewall configurations)

These are **authorized security testing environments** for defensive security training and CTF challenges. All vulnerable components are containerized and intended for controlled lab environments.
