# RANGE42

**range42** is a modular cyber range platform based on Proxmox + Ansible for deploying reproducible offensive, defensive and hybrid training environments.
One operator workstation can manage multiple Proxmox infrastructures, each running multiple lab scenarios. Everything is infrastructure-as-code.

Start with [GETTING_STARTED.md](GETTING_STARTED.md) for a hands-on walkthrough, or browse the [GLOSSARY](GLOSSARY.md) for terminology (codename, scenario, workspace, jump host, etc.).

## Table of contents

- [Start here](#start-here)
  - [Quick start](#quick-start)
  - [Supported platforms](#supported-platforms)
  - [Daily operations](#daily-operations)
- [About the project](#about-the-project)
  - [Who it's for](#who-its-for)
  - [Architecture overview](#architecture-overview)
  - [The stack](#the-stack)
  - [Project mid / long term goals](#project-mid--long-term-goals)
  - [Extend the scenarios](#extend-the-scenarios)
  - [Glossary](#glossary)
  - [Authors](#authors)

---

# Start here

## Quick start

The recommended way to deploy range42 is the setup wizard:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-venv git
mkdir -p $HOME/range42 && cd $HOME/range42
git clone https://github.com/range42/range42.git
cd range42
./range42-init.py
```

![range42 setup wizard](docs/img/old/0002.png)

The wizard walks you through preflight checks, Proxmox connection, network configuration and the full deployment.

For the complete walkthrough (prerequisites, every wizard step explained, SSH access, daily operations, troubleshooting), see [GETTING_STARTED.md](GETTING_STARTED.md).

If you'd rather drive the playbooks yourself, see [Manual setup (advanced)](GETTING_STARTED.md#manual-setup-advanced).

## Supported platforms

range42 is developed and tested on Ubuntu LTS (Desktop / Server) and is also expected to work on Debian 13. Full details and prerequisites:
[GETTING_STARTED.md - Prerequisites](GETTING_STARTED.md#prerequisites).

## Daily operations

Once deployed, you manage your lab with the `range42-context` shell tool (switch workspaces, deploy / undeploy, SSH into VMs, view credentials, etc.). The full reference is in
[OPERATIONS.md](OPERATIONS.md).

---

# About the project

## Who it's for

- **Sysadmins** - practice securing vulnerable stacks and test hardening procedures
- **SOC analysts / blue teams** - validate detection rules, tune alerts, test incident response
- **Red teamers / researchers** - build exploit chains, study CVEs in controlled environments
- **Forensics teams** - reconstruct incidents, analyse compromised systems

## Architecture overview

A range42 deployment can be driven in two complementary ways:

**Web UI path** (visual, recommended for day-to-day operations):

```
  ┌─ range42-deployer-ui (Vue 3 + VueFlow) ──────────────────┐
  │  Visual topology canvas — drag-and-drop lab design        │
  └──────────────────────────┬───────────────────────────────┘
                             │ REST + WebSocket
  ┌──────────────────────────▼───────────────────────────────┐
  │  range42-api-gw (Kong gateway)                           │
  │  Auth, ACLs, rate-limiting                               │
  └──────────────────────────┬───────────────────────────────┘
                             │
  ┌──────────────────────────▼───────────────────────────────┐
  │  range42-backend-api (FastAPI)                           │
  │  80 REST endpoints + /ws/status stream                   │
  └──────────┬───────────────────────┬───────────────────────┘
             │                       │
  range42-playbooks          range42-catalog
  (scenarios + bundles)      (roles, Docker, CTF content)
             │
             ▼
  [ Proxmox VE cluster ]
  VMs, LXC, networks
```

**CLI path** (direct, for advanced/scripted use):

```
  [ deployer-cli (range42-context) ]
     │
     ├─ runs the setup wizard
     ├─ holds inventory + credentials
     └─ drives Ansible playbooks directly
             │
             ▼
  [ Proxmox VE cluster ]
  VMs, LXC, networks
```

Both paths converge on the same Proxmox infrastructure and Ansible playbooks — the web UI simply adds a visual layer and a managed API on top.

The **deployer-cli** is your local machine by default, or a dedicated pivot VM if you manage multiple Proxmox infrastructures from one place.

Today, the **lab VMs on Proxmox** are generally organised into 3 host groups (this is the convention used by current scenarios and may evolve as new ones are added):

| Group | Purpose | Required |
|-------|---------|----------|
| **Vulnerable targets** | Core lab systems for attack and analysis | Yes |
| **Administration** | Monitoring, orchestration, supervision | No |
| **Student / Training** | Workstations for learners | No |

Only the vulnerable hosts group is required - admin and student groups are optional and can be disabled to save resources.

## The stack

In its recommended configuration, range42 relies on:

- **Proxmox** - hypervisor for virtual machines (mandatory)
- **Ansible** - provisioning and orchestration (mandatory)
- **Docker / LXC** - containerized services and vulnerable stacks (recommended)
- **Wazuh** - security monitoring and detection (optional)
- **Firewalls / VPN** - network segmentation and access control (recommended)
- **Vue.js / FastAPI / Kong** - web UI and API layer (available)

## Project mid / long term goals

The goal is to cover the full spectrum of cyber training. Here's where the project stands today and where it's heading.

**Status legend:** **shipping** = production-tested · **early** = working, content to grow · **partial** = code in place, currently disabled · **planned** = on the roadmap

| Use case | Status | What range42 brings |
|----------|--------|---------------------|
| **Network labs** | shipping | Empty multi-subnet bases (`blank_scenario_2/4/6_subnets`) ready for you to install your own workloads on top |
| **Defensive training** | shipping | Wazuh-instrumented infrastructure via `demo_lab`, ready for detection-engineering and rule-tuning exercises |
| **Offensive training** | early | Vulnerable hosts and misconfigured services in `demo_lab`; an extensible catalogue of CVEs and product setups **will** grow over upcoming releases |
| **Student workstations** | partial | Group structure in place; the `03_student_infrastructure` block is currently disabled and **will** be re-enabled once stabilised |
| **Hybrid (red / blue)** | planned | One lab, both perspectives, scoreboard and full visibility on both sides |
| **Forensics & IR** | planned | Reproducible compromised environments for rebuild-and-investigate exercises |

## Extend the scenarios

All deployable scenarios live in [range42-playbooks/scenarios](https://github.com/range42/range42-playbooks/tree/main/scenarios) - the list will grow over time.

The reusable building blocks (CVEs, misconfigured services, product setups, Ansible roles) live in the [range42-catalog](https://github.com/range42/range42-catalog) repository.

**Want a specific product, CVE or misconfiguration added?** Open an issue on the [range42-catalog](https://github.com/range42/range42-catalog/issues) repo - we centralise catalog requests there.

**Found a bug or have a feature request for range42 itself?** Open an issue on the [range42](https://github.com/range42/range42/issues) repo (anything not related to the catalog goes here).

We'll prioritise as fast as we can.

## Glossary

See [GLOSSARY.md](GLOSSARY.md) for all terminology: codename, scenario, workspace,
deployer-cli, jump host, vault, context, range42-context, host groups, inventory.

## Authors

range42 is built and maintained by:

| Name | Company / Affiliation | Website |
|------|----------------------|---------|
| Benjamin Collas | DIGISQUAD | [digisquad.com](https://www.digisquad.com) |
| Philippe Parage | NC3 | [nc3.lu](https://nc3.lu/) |

See AUTHORS file for the full list of contributors.
