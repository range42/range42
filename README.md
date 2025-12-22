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
- a **dedicated deployment virtual machine** running externally to the Proxmox host.
- a dedicated **deployment laptop**  

This is a recommendation, not a strict requirement, but it helps maintain better isolation, resource control and resilience during provisioning operations.

# INSTALLATION  

```bash
soon pushed.
```

# AUTHORS

```bash
soon pushed.
```