# proxmox.ssh-limits

Raises the Proxmox (jump host) sshd pre-auth concurrency limit so that parallel
Ansible connections reaching many VMs through the single `ProxyJump` are not
dropped by the default `MaxStartups 10:30:100`.

## Why

Scenario deploys open up to `forks` SSH connections at once, all transiting the
Proxmox jump host. Beyond 10 concurrent pre-auth connections the default sshd
drops a random fraction, which surfaces as intermittent
`Connection closed by UNKNOWN port 65535` at `Gathering Facts` (range42 #231).

## What it does

- Writes an isolated drop-in `/etc/ssh/sshd_config.d/60-range42-jump-concurrency.conf`
  containing only `MaxStartups` (never edits the main `sshd_config`).
- Reloads sshd so the new limit takes effect.

## Safety

- The rendered drop-in is validated (`sshd -t -f`) **before** it is moved into
  place: a malformed value never lands on disk.
- Preflight guards abort if ssh is socket-activated or if `sshd_config` does not
  `Include` the drop-in directory.
- Reload only (never restart): the unit `ExecReload=sshd -t` refuses an invalid
  config and keeps the previous one; existing connections are preserved.
- On any failure after the write, the drop-in is removed and sshd reloaded back
  to its previous config.
- Idempotent: no change and no reload when the drop-in is already correct.

## Variables

| var | default | meaning |
|---|---|---|
| `proxmox_ssh_limits_maxstartups` | `100:30:200` | `MaxStartups` value (`start:rate:full`) |
| `proxmox_ssh_limits_dropin` | `/etc/ssh/sshd_config.d/60-range42-jump-concurrency.conf` | managed drop-in path |

## Manual rollback

```bash
rm /etc/ssh/sshd_config.d/60-range42-jump-concurrency.conf
systemctl reload ssh
```
