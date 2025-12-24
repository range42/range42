# Repository Guidelines

## Project Structure & Module Organization
- `prepare-infrastructure-workspace.sh` is the main entrypoint for generating inventories, vaults, and deployer-cli playbooks.
- `config/` holds the master YAML configuration and helper vault scripts.
- `roles/configure.deployer-cli/` contains the Ansible role that configures a deployer CLI host (tasks, templates, defaults, and files).
- `utils/` provides local shell helpers for SSH agent setup.

## Build, Test, and Development Commands
- Workspace prep: `./prepare-infrastructure-workspace.sh` reads `config/config_remote-deployer-cli.MASTER_FILE.yml` and emits inventories, vaults, and deploy scripts.
- Role execution: use the generated `deploy.<host>-<scenario>.sh` script or run `ansible-playbook -i inventories/<host>.yml deploy.<host>-<scenario>.yml -K`.
- Vault tooling: `./config/vault.create.sh`, `./config/vault.edit.sh`, `./config/vault.view.sh`, `./config/vault.changepwd.sh`.

## Coding Style & Naming Conventions
- Shell scripts are bash; keep the current formatting style and safety flags when editing.
- Ansible YAML uses two-space indentation; keep the numbered task file sequencing under `roles/configure.deployer-cli/tasks/`.
- Templates live under `roles/configure.deployer-cli/templates/` and should stay parameterized (avoid hardcoding environment values).

## Testing Guidelines
- No automated tests are defined; validate changes by running the workspace prep script and the generated Ansible playbook in a safe environment.

## Commit & Pull Request Guidelines
- Use imperative, component-prefixed subjects (e.g., `role: adjust deployer-cli git config`, `scripts: tighten workspace prep`).
- Mention any impacted configuration files or templates in the body.
