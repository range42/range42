# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `gh-repo-organizer` project.

## Project Overview

This project is a collection of Ansible roles and scripts designed to set up a deployment machine (or "jump host") for managing a cyber-range environment called RANGE42.

**Key Technologies:**

*   **Automation:** Ansible is the core technology used for configuration management and orchestration.
*   **Virtualization:** The cyber range itself is built on Proxmox.
*   **Containerization:** Docker and LXC may be used to run specific services.
*   **Monitoring:** Wazuh is used for security event monitoring.
*   **Web Stack:** A Vue.js frontend and Python/FastAPI backend are optional components.

**Project Structure:**

*   `roles/`: Contains the Ansible roles for configuring the deployment machine.
    *   `roles/configure.deployer-cli/`: The main role for this project.
        *   `tasks/`: Contains the Ansible tasks for setting up the environment.
*   `config/`: Contains configuration files for the deployment.
*   `utils/`: Contains utility scripts.
*   `prepare-infrastructure-workspace.sh`: The main entry point script for setting up the workspace.

## Building and Running

There is no traditional "build" process for this project. The primary action is to execute the `prepare-infrastructure-workspace.sh` script, which in turn runs an Ansible playbook to configure the deployment machine.

**Key Commands:**

*   `./prepare-infrastructure-workspace.sh`: This is the main script to set up the deployment environment. It likely runs the Ansible playbook located in this repository.

To understand the specific steps involved in the setup process, refer to the Ansible tasks in the `roles/configure.deployer-cli/tasks/` directory. The `main.yml` file in that directory provides the main execution flow.

## Development Conventions

*   **Ansible Roles:** The project is structured using Ansible roles, promoting modularity and reusability.
*   **Variable-driven Configuration:** Configuration is managed through Ansible variables. Key variables can be found in `roles/configure.deployer-cli/defaults/main.yml` and in the `config/` directory.
*   **Task-oriented structure:** The Ansible tasks are broken down into small, single-purpose YAML files, making the automation easier to understand and maintain.
*   **Development Mode:** The project includes a `DEV_MODE` option, which can be enabled to alter the setup process for development purposes.
