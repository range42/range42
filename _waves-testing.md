# Waves testing

This file is identical across all `range42/*` repositories - it gives the
same cross-repo view from wherever you land. It indexes the umbrella
tracking issues per release wave; each umbrella contains the full detail
(PRs, sub-issues, commits, integration test plan) for its repo.

A WAVE is a deploy-test identifier, not a release version. It groups issues
that were validated end-to-end by deploying one or more scenarios on a real
Proxmox - not just quick fixes merged without test coverage. Date = final
test sign-off (YYYY-MM-DD). No date = wave still in progress.

A wave can have 1 or several umbrellas - typically one per repo touched by
the wave (e.g. WAVE_01 has 3 umbrellas across 3 repos). A single umbrella
covering cross-repo work is also valid (e.g. WAVE_02 has 1 umbrella on
playbooks that also tracks devkit work via SHA refs in its body).

## WAVE_03 - in progress

- range42/range42-playbooks#62
- range42/range42#174
- range42/range42-ansible_roles-debug-devkit#110
- range42/range42-catalog#164

## WAVE_02 - 2026-05-22

- range42/range42-playbooks#55

## WAVE_01 - 2026-05-20

- range42/range42#162
- range42/range42-playbooks#49
- range42/range42-ansible_roles-proxmox_controller#98
