# _legacy/

Archived files from the v1 monolithic deployment approach.

These files have been replaced by:
- `prepare-infrastructure-workspace.sh` → roles/credentials.*, roles/proxmox.*
- `deploy.range42.*.yml` → playbooks/01-03 + site.yml
- `deploy.range42.*.sh` → playbooks/01-03 + site.yml
- `_debug.clean_up.sh` → no longer needed

The role `roles/configure.deployer-cli/` is also legacy but kept in place
until all new roles are validated in production.

See `playbooks/` and `site.yml` for the new deployment approach.
