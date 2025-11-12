# RANGE42 

**RANGE42** is a modular cyber range platform for building and deploying realistic cyber training infrastructures on-premises. The project is still at an early stage but it’s open source and contributions are welcome!

**Currently RANGE42 provide two main capabilities :**
 - **Deploy vulnerable and misconfigured hosts.**
 - **Include an extensible catalogue of ready-to-deploy CVEs, misconfigured services and product setup.**

Soon : 
 - Web Infrastructure designer UI : draw a network and deploy it automatically
 - An extended catalog of ready to deploy scenarios including various CVE and more.

# FOR WHO AND WHY ?

Our goal is to let anyone in cyber security test, break, and analyse realistic scenarios from system hardening to full compromise and incident response.

A few examples : 

- **Sysadmins / network admins** could practice securing vulnerable stacks and test hardening procedures
- **SOC analysts / blue teams** could validate detection rules, tune alerts and test Incident response workflows
- **Red teamers / security researchers** could build exploit chains or study CVEs in controlled environments
- **Forensics teams / investigators** could reconstruct incidents and analyse compromised systems through practical drills

# ARCHITECTURE OVERVIEW

In its recommended full configuration, **RANGE42** relies on the following technology layers:

- ``Hypervisor Layer`` : **Proxmox** used to provision and manage the underlying virtual machines. *(mandatory)*
- ``Automation Layer`` : **Ansible** handles provisioning, configuration management and orchestration of systems. *(mandatory)*
- ``Container Layer`` : **Docker / LXC** used to run specific services, intentionally misconfigured components, or application stacks. *(recommended)*
- ``Monitoring Layer`` : **Wazuh** collects security events, logs, alerts and detection data. *(optional)*
- ``Network Layer`` : **Firewalls**, **VPN** overlays and segmentation controls to ensure isolated and secure lab access. *(recommended)*
- ``Web Applications & API Layer`` : **Vue.js** frontend, **Python3** & **FastAPI** backend with **Kong** as API gateway. *(optional)*

## HOSTS GROUPING

To structure the environment from an operational standpoint, the infrastructure is divided into three host groups:

| Group | Default Purpose | Can be Disabled? |
|--------|-----------------|----------------|
| **Administration** | UI orchestration, monitoring, and supervision | **Yes** |
| **Vulnerable targets** | Core lab systems used for attack and analysis | **No** |
| **Student / Training** | Workstations and practice machines for learners | **Yes** |


For testing, development, or environments with limited hardware, the "admin hosts group" and "student hosts group" can be reduced or omitted during deployment. Only the "vulnerable hosts group" is strictly required for running core scenarios.

Disabling or minimizing these auxiliary groups helps reduce CPU, RAM, and disk usage on the hypervisor while still allowing full offensive/defensive experimentation on the vulnerable systems.

## DEPLOYMENT MACHINE

To deploy the laboratory environment, a **deployment machine** is required.  
For several reasons, we **recommend not running this deployment machine directly on the hypervisor** itself.  

Instead, prefer using either:
- a dedicated **deployment laptop** OR  
- a **dedicated deployment virtual machine** running externally to the Proxmox host.

This is a recommendation, not a strict requirement, but it helps maintain better isolation, resource control and resilience during provisioning operations.

## DEFAULT ADDRESSING AND NAMING CONVENTION

By default, and in its full configuration, the infrastructure deployed on Proxmox follows the addressing and naming convention described below.  
These defaults can be adapted as needed, but they provide a consistent baseline for orchestration and automation.

### Vulnerable Hosts Group

| Hostname | IP Address | VM ID (proxmox) |
|-----------|-------------|-------------|
| r42.vuln-box-00 | 192.168.42.170 | 4000 |
| r42.vuln-box-01 | 192.168.42.171 | 4001 |
| r42.vuln-box-02 | 192.168.42.172 | 4002 |
| r42.vuln-box-03 | 192.168.42.173 | 4003 |
| r42.vuln-box-04 | 192.168.42.174 | 4004 |

### Student Hosts Group

| Hostname | IP Address | VM ID (proxmox) |
|-----------|-------------|-------------|
| r42.student-box-01 | 192.168.42.160 | 3001 |

### Administration Hosts Group

| Hostname | IP Address | VM ID (proxmox) |
|-----------|-------------|-------------|
| r42.admin-builder-api-devkit | 192.168.42.102 | - |
| r42.admin-builder-docker-registry | 192.168.42.101 | - |
| r42.admin-wazuh | 192.168.42.100 | 1000 |
| r42.admin-web-api-kong | 192.168.42.120 | 1020 |
| r42.admin-web-builder-api | 192.168.42.121 | 1021 |
| r42.admin-web-deployer-ui | 192.168.42.123 | 1023 |


# INSTALLATION

## DEPLOYMENT TYPES

The project relies heavily on Ansible to deploy the lab environment.

We recommend several methods for accessing the lab from the deployment machine. Each mode has trade offs in terms of simplicity, flexibility and security. Note that while Mode 3 appears more complex, it is often the most flexible option.

The "mode 3" also lets you optionally expose vulnerable machines over a VPN/mesh overlay which can simplify access when hosts are behind NAT or strict firewalls.

This project supports three access modes to **RANGE42**:

| Mode | Internal name | Description | Network flow |
|------|---------------|-------------|--------------|
| **Mode 1** | minimal | Direct SSH connection, no intermediary. | local → target |
| **Mode 2** | jump | Access via a classic SSH bastion/jump host. | local → bastion → target |
| **Mode 3** | jump-tailscale | Access via a Tailscale node acting as a bastion/jump host (mesh VPN). | local → Tailscale node → target |

## DEPLOYMENT TYPE 1 - `minimal mode`
Direct communication between the deployment machine and all lab hosts (not recommanded setup). 

Installation script : 
```bash
soon pushed.
```

## DEPLOYMENT TYPE 2 - `jump mode`

All traffic from the deployment machine is routed through an intermediate SSH bastion (via ProxyJump).  
This mode is suitable when the lab is hosted in a segmented network or when direct access to target hosts is restricted.

It is also useful in more advanced setups where you may:
- operate multiple Proxmox nodes distributed across different network zones 
- deploy splitted lab environments for multiple isolated teams that must remain mutually inaccessible by administrators

Installation script : 
```bash
soon pushed.
```

## DEPLOYMENT TYPE 3 - `jump-tailscale`

All SSH traffic from the deployment machine is routed through a Tailscale "node" acting as a VPN and access-control layer.  
This mode establishes a private, encrypted zero-trust mesh network between the deployment host and all lab systems without requiring any public IPs or inbound firewall rules.

Authentication and access control are managed through third-party identity providers (like github) and can enforce multi-factor authentication (MFA) for each connection.

This provides an additional layer of security and  maintaining connectivity across different locations or network boundaries.

Such a configuration is ideal for:
- **Hybrid deployments** : on-prem + cloud + remote nodes
- **Distributed or multi-team labs** :  where each segment can use its own authenticated Tailscale node  
- **Restricted or NATed environments** : where direct SSH access would otherwise be impossible

Installation script : 
```bash
soon pushed.
```


# AUTHORS

todo.
