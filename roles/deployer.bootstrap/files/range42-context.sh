#!/usr/bin/env zsh
################################################################################
# range42-context — workspace context manager (zsh function)
#
# This file is SOURCED in .zshrc, not executed as a script.
# All functions run in the current shell process — they can modify
# environment variables, source files, and update the prompt.
#
# Usage:
#   range42-context list                          — list available workspaces
#   range42-context current                       — show active workspace
#   range42-context use <codename> <scenario>     — switch workspace (T46)
#   range42-context ssh-reload                    — reload SSH keys (T45)
#   range42-context help                          — show help
#
# Sourced by deployer.bootstrap via .zshrc (T47)
#
################################################################################

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# constants
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

RANGE42_SSH_CONFIG_FILE="$HOME/.ssh/config"
RANGE42_SSH_BEGIN_MARK='^#### BEGIN RANGE42 INCLUDE'
RANGE42_SSH_END_MARK='^#### END RANGE42 INCLUDE'
RANGE42_CONFIG_BASE_DIR="${RANGE42_CONFIG_BASE_DIR:-$HOME/range42.config}"

# banner on load
_r42_last_workspace="$(sed -n "/$RANGE42_SSH_BEGIN_MARK/,/$RANGE42_SSH_END_MARK/{/^[[:space:]]*Include /{s@.*config_range42-@@;s@[[:space:]].*@@;p;}}" "$RANGE42_SSH_CONFIG_FILE" 2>/dev/null | head -1)"
printf "\n\033[1;32m  deployer-cli ready\033[0m\n"
if [[ -n "$_r42_last_workspace" ]]; then
    # split CODENAME-SCENARIO: scenario is after the last known separator
    local _last_scenario _last_codename
    for _sd in "$RANGE42_CONFIG_BASE_DIR/$_r42_last_workspace"/; do
        if [[ -d "$_sd" ]]; then
            # find scenario from scenario dir in range42-playbooks
            for _pd in "$HOME/range42/range42-playbooks/scenarios"/*/; do
                _last_scenario="$(basename "$_pd")"
                if [[ "$_r42_last_workspace" == *"-${_last_scenario}" ]]; then
                    _last_codename="${_r42_last_workspace%-${_last_scenario}}"
                    break 2
                fi
            done
        fi
    done
    if [[ -n "$_last_codename" && -n "$_last_scenario" ]]; then
        printf "\n\033[0;90m  INFO  load previous workspace:\033[0m\n"
        printf "\033[0;37m        range42-context use %s %s\033[0m\n" "$_last_codename" "$_last_scenario"
    fi
fi
unset _r42_last_workspace _last_scenario _last_codename
printf "\n\033[0;90m  INFO  all commands:\033[0m\n"
printf "\033[0;37m        range42-context help\033[0m\n\n"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# display helpers
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_print_section() {
    printf "\n\033[34m----[ %s ]----\033[0m\n\n" "$1"
}

_r42_print_step() {
    printf "    \033[34m➜\033[0m %s\n" "$1"
}

_r42_print_check() {
    printf "    \033[32m✓\033[0m %s\n" "$1"
}

_r42_print_fail() {
    printf "    \033[31m✗\033[0m %s\n" "$1"
}

_r42_print_warning() {
    printf "    \033[31m▲\033[0m %s\n" "$1"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context current — show active workspace
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_current() {

    local active_targets

    active_targets="$(
        sed -n \
            "/$RANGE42_SSH_BEGIN_MARK/,/$RANGE42_SSH_END_MARK/ {
            /^[[:space:]]*Include / {
                s@.*config_range42-@@
                s@[[:space:]].*@@
                p
            }
        }" "$RANGE42_SSH_CONFIG_FILE" | sort -u
    )"

    if [[ -z "$active_targets" ]]; then
        _r42_print_warning "active workspace is: NOT SET"
        return 1  # FIX P1: return instead of exit (function, not script)
    fi

    printf "%s\n" "${active_targets}"
    return 0
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context list — list available workspaces
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_list() {

    _r42_print_section "available workspaces"

    # method 1: from ssh config (Include lines, commented or not)
    local ssh_targets
    ssh_targets="$(
        sed -n \
            "/$RANGE42_SSH_BEGIN_MARK/,/$RANGE42_SSH_END_MARK/{
            /^[[:space:]]*#*[[:space:]]*Include /{
                s@.*config_range42-@@
                s@[[:space:]].*@@
                p
            }
        }" "$RANGE42_SSH_CONFIG_FILE" | sort -u
    )"

    # method 2: from filesystem (range42.config directories)
    local fs_targets
    fs_targets="$(
        ls -1d "$RANGE42_CONFIG_BASE_DIR"/*/ 2>/dev/null |
        xargs -I{} basename {} |
        sort -u
    )"

    # merge both sources, deduplicate
    local all_targets
    all_targets="$(printf "%s\n%s\n" "$ssh_targets" "$fs_targets" | grep -v '^$' | sort -u)"

    # show with active marker
    local current
    current="$(_r42_current 2>/dev/null)"

    local target
    local _idx=0
    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"

    echo "  ──────────────────────────────────────────────────────────────"

    for target in ${(f)all_targets}; do
        # skip empty lines
        [[ -z "$target" ]] && continue

        _idx=$((_idx + 1))

        # split workspace name into codename + scenario
        local _scenario="" _codename="" _use_cmd=""
        for _pd in "${git_dir%/}/range42-playbooks/scenarios"/*/; do
            _scenario="$(basename "$_pd")"
            if [[ "$target" == *"-${_scenario}" ]]; then
                _codename="${target%-${_scenario}}"
                _use_cmd="range42-context use ${_codename} ${_scenario}"
                break
            fi
            _scenario=""
        done

        # skip entries where codename could not be resolved
        [[ -z "$_codename" ]] && continue

        if [[ "$target" == "$current" ]]; then
            printf "  \033[1;32m● [%d]  %-35s  %s\033[0m\n" "$_idx" "$target" "$_use_cmd"
        else
            printf "  \033[0;90m○ [%d]  %-35s  %s\033[0m\n" "$_idx" "$target" "$_use_cmd"
        fi
    done

    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context flush known_hosts — remove stale host keys for a workspace
#
# Extracts all Hostname IPs from the workspace's SSH config file and removes
# them from known_hosts. This prevents "REMOTE HOST IDENTIFICATION HAS CHANGED"
# errors when switching between infrastructures that share the same VM IPs.
#
# Called by: _r42_use, _r42_deploy, _r42_deploy_vms
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_flush_known_hosts() {
    local target="${1:-}"

    # Source of truth = the scenario manifest (manifest/scenario_vms.json).
    # Only flush IPs of the scenario's VMs — never the Proxmox host (which is
    # referenced as ProxyJump and shouldn't change between deploys).
    local config_dir="$RANGE42_CONFIG_BASE_DIR/$target"
    local scenario_link="$config_dir/scenario"
    if [[ ! -L "$scenario_link" ]]; then
        return 0
    fi

    local manifest="$(readlink -f "$scenario_link")/manifest/scenario_vms.json"
    if [[ ! -f "$manifest" ]]; then
        # fallback : workspace/scenario without manifest yet — silently skip
        return 0
    fi

    local flushed=0
    while IFS= read -r ip; do
        [[ -z "$ip" ]] && continue
        ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$ip" >/dev/null 2>&1
        flushed=$((flushed + 1))
    done < <(jq -r '.vms[].ip' "$manifest")

    _r42_print_step "flushed known_hosts for $target ($flushed VM IPs)"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context ssh-reload — reload SSH keys for active workspace (T45)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_ssh_reload() {

    local verbose="${1:-}"

    # check ssh-agent
    if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
        _r42_print_fail "ssh-agent is not running (SSH_AUTH_SOCK not set)"
        _r42_print_warning "run: eval \`keychain --eval id_rsa\`"
        return 1
    fi

    # unload all keys
    ssh-add -D 2>/dev/null

    # get active workspace
    local workspace
    workspace="$(_r42_current)" || {
        _r42_print_warning "cannot reload SSH keys: no active workspace"
        return 1
    }

    # parse active ssh config for IdentityFile entries
    # FIX P4: trim leading whitespace from IdentityFile paths
    local key_count=0
    grep '^Include ' "$RANGE42_SSH_CONFIG_FILE" |
        grep 'config_range42' |
        grep -v '^#' |
        sed 's/^Include //' |
        while read -r config_file; do
            grep 'IdentityFile ' "$config_file" 2>/dev/null |
                sed 's/^[[:space:]]*IdentityFile[[:space:]]*//' |
                sort -u |
                while read -r identity_file; do
                    if [[ "$verbose" == "-v" ]]; then
                        _r42_print_warning "loading: $identity_file"
                    fi
                    ssh-add "$identity_file" </dev/tty 2>/dev/null
                    key_count=$((key_count + 1))
                done
        done

    local loaded
    loaded=$(ssh-add -l 2>/dev/null | wc -l)
    _r42_print_check "ssh keys reloaded ($loaded key(s) loaded)"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context use — switch active workspace (T46)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_use() {

    local codename="$1"
    local scenario="$2"

    if [[ -z "$codename" || -z "$scenario" ]]; then
        _r42_print_fail "usage: range42-context use <codename> <scenario>"
        return 1
    fi

    local target="${codename}-${scenario}"
    local config_dir="$RANGE42_CONFIG_BASE_DIR/$target"

    # verify workspace exists
    if [[ ! -d "$config_dir" ]]; then
        _r42_print_fail "workspace not found: $config_dir"
        _r42_print_warning "available workspaces:"
        _r42_list
        return 1
    fi

    _r42_print_section "switching to $target"

    #### ssh config switch — comment all, uncomment target

    sed -i "/$RANGE42_SSH_BEGIN_MARK/,/$RANGE42_SSH_END_MARK/ s/^Include /# Include /" \
        "$RANGE42_SSH_CONFIG_FILE"
    _r42_print_step "commented all active Include lines"

    sed -i "/$RANGE42_SSH_BEGIN_MARK/,/$RANGE42_SSH_END_MARK/ s/^# Include \(.*config_range42-${target}.*\)/Include \1/" \
        "$RANGE42_SSH_CONFIG_FILE"
    _r42_print_step "uncommented Include for $target"

    #### zshrc switch — comment all sourced_range42.sh, uncomment target
    # ensures the correct workspace is sourced on next login too

    sed -i 's|^[# ]*source "\(.*sourced_range42\.sh\)"|#source "\1"|' \
        "$HOME/.zshrc"
    _r42_print_step "commented all sourced_range42.sh in .zshrc"

    sed -i "s|^#source \"\(.*/${target}/sourced_range42\.sh\)\"|source \"\1\"|" \
        "$HOME/.zshrc"
    _r42_print_step "uncommented sourced_range42.sh for $target in .zshrc"

    #### source the workspace environment directly in this shell (no restart needed)

    local sourced_file="$config_dir/sourced_range42.sh"
    if [[ -f "$sourced_file" ]]; then
        source "$sourced_file"
        _r42_print_step "sourced $sourced_file"
    else
        _r42_print_warning "sourced_range42.sh not found in $config_dir"
    fi

    #### update secrets symlinks in git repos to point to the active workspace

    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"
    local devkit_secrets="${git_dir%/}/range42-ansible_roles-debug-devkit/secrets"
    local playbooks_secrets="${git_dir%/}/range42-playbooks/scenarios/${scenario}/secrets"

    if [[ -d "${git_dir%/}/range42-ansible_roles-debug-devkit" ]]; then
        ln -sfn "$config_dir/secrets" "$devkit_secrets"
        _r42_print_step "updated secrets symlink in devkit → $target"
    fi
    if [[ -d "${git_dir%/}/range42-playbooks/scenarios/${scenario}" ]]; then
        ln -sfn "$config_dir/secrets" "$playbooks_secrets"
        _r42_print_step "updated secrets symlink in playbooks → $target"
    fi

    #### flush known_hosts for the target workspace (avoid stale host keys on multi-infra)

    _r42_flush_known_hosts "$target"

    #### export vault password file path (T46b)

    local vault_pass_file="$config_dir/secrets/vault_pass.txt"
    if [[ -f "$vault_pass_file" ]]; then
        export RANGE42_VAULT_PASSWORD_FILE="$vault_pass_file"
        _r42_print_step "exported RANGE42_VAULT_PASSWORD_FILE=$vault_pass_file"
    else
        _r42_print_warning "vault_pass.txt not found in $config_dir/secrets/"
    fi

    #### export active workspace info

    export RANGE42_ACTIVE_WORKSPACE="$target"
    export RANGE42_ACTIVE_CONFIG_DIR="$config_dir"

    #### export ansible config so our settings apply everywhere (suppress warnings etc.)
    local r42_ansible_cfg="$HOME/range42/range42/ansible.cfg"
    if [[ -f "$r42_ansible_cfg" ]]; then
        export ANSIBLE_CONFIG="$r42_ansible_cfg"
        _r42_print_step "exported ANSIBLE_CONFIG=$r42_ansible_cfg"
    fi

    #### update zsh prompt to show active workspace (green tag)

    export RANGE42_PROMPT_TAG="%F{green}[r42:${target}]%f"
    if [[ "$PROMPT" != *"RANGE42_PROMPT_TAG"* ]]; then
        export PROMPT='${RANGE42_PROMPT_TAG} '"${PROMPT}"
    fi

    #### reload ssh keys

    _r42_ssh_reload

    #### show status after switch

    _r42_status
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context inventory — show ansible inventory tree
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_inventory() {

    local inventory_dir="${RANGE42_ANSIBLE_ROLES__INVENTORY_DIR:-}"

    if [[ -z "$inventory_dir" ]]; then
        _r42_print_fail "no active workspace (RANGE42_ANSIBLE_ROLES__INVENTORY_DIR not set)"
        _r42_print_warning "run: range42-context use <codename> <scenario>"
        return 1
    fi

    local inventory_file="${inventory_dir%/}/inventory_default.yml"

    if [[ ! -f "$inventory_file" ]]; then
        _r42_print_fail "inventory not found: $inventory_file"
        return 1
    fi

    _r42_print_section "ansible inventory — ${RANGE42_ACTIVE_WORKSPACE:-unknown}"
    ansible-inventory -i "$inventory_file" --graph
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context cd — navigate to workspace directories
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_cd() {
    local target="${1:-config}"
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"

    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        _r42_print_warning "run: range42-context use <codename> <scenario>"
        return 1
    fi

    case "$target" in
        config)
            cd "$config_dir" && _r42_print_check "cd $config_dir"
            ;;
        scenario)
            if [[ -L "$config_dir/scenario" ]]; then
                cd "$config_dir/scenario" && _r42_print_check "cd $(readlink -f "$config_dir/scenario")"
            else
                _r42_print_fail "scenario symlink not found in $config_dir"
                return 1
            fi
            ;;
        secrets|vault)
            cd "$config_dir/secrets" && _r42_print_check "cd $config_dir/secrets"
            ;;
        *)
            _r42_print_fail "unknown target: $target"
            echo "  usage: range42-context cd [config|scenario|secrets]"
            return 1
            ;;
    esac
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context status — check workspace health
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_status() {

    local workspace="${RANGE42_ACTIVE_WORKSPACE:-}"
    if [[ -z "$workspace" ]]; then
        _r42_print_fail "no active workspace"
        _r42_print_warning "run: range42-context use <codename> <scenario>"
        return 1
    fi

    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    local vault_pass="${RANGE42_VAULT_PASSWORD_FILE:-}"
    local vault_file="$config_dir/secrets/default_vault.yml"
    local inv_file="$config_dir/inventory/inventory_default.yml"

    # status line helper: component, value, ok/fail
    _s_ok()   { printf "    \033[1;37m%-16s\033[0m %-36s \033[1;32m%s\033[0m\n" "$1" "$2" "$3"; }
    _s_fail() { printf "    \033[1;37m%-16s\033[0m %-36s \033[1;31m%s\033[0m\n" "$1" "$2" "$3"; }
    _s_warn() { printf "    \033[1;37m%-16s\033[0m %-36s \033[1;33m%s\033[0m\n" "$1" "$2" "$3"; }

    echo ""
    printf "    \033[1;34m--- status : %s ---\033[0m\n" "$workspace"
    echo ""

    # workspace
    _s_ok "workspace" "$workspace" "ok"

    # vault password
    if [[ -n "$vault_pass" && -f "$vault_pass" ]]; then
        _s_ok "vault pass" "vault_pass.txt" "ok"
    else
        _s_fail "vault pass" "${vault_pass:-not set}" "missing"
    fi

    # vault encrypted
    if [[ -f "$vault_file" ]]; then
        if head -1 "$vault_file" | grep -q '^\$ANSIBLE_VAULT'; then
            _s_ok "vault" "encrypted" "ok"
        else
            _s_warn "vault" "NOT encrypted (cleartext)" "warn"
        fi
    else
        _s_fail "vault" "not found" "missing"
    fi

    # vault decryptable
    if [[ -f "$vault_file" && -f "$vault_pass" ]]; then
        if ansible-vault view "$vault_file" --vault-password-file "$vault_pass" >/dev/null 2>&1; then
            _s_ok "vault decrypt" "password valid" "ok"
        else
            _s_fail "vault decrypt" "wrong password?" "fail"
        fi
    fi

    # ssh agent
    if [[ -n "${SSH_AUTH_SOCK:-}" ]] && ssh-add -l >/dev/null 2>&1; then
        local key_count
        key_count=$(ssh-add -l | wc -l)
        _s_ok "ssh-agent" "$key_count key(s) loaded" "ok"
    else
        _s_fail "ssh-agent" "no keys loaded" "fail"
    fi

    # inventory
    if [[ -f "$inv_file" ]]; then
        _s_ok "inventory" "inventory_default.yml" "ok"
    else
        _s_fail "inventory" "not found" "missing"
    fi

    # scenario symlink
    if [[ -L "$config_dir/scenario" ]]; then
        _s_ok "scenario" "$(basename "$(readlink "$config_dir/scenario")")" "ok"
    else
        _s_warn "scenario" "symlink missing" "warn"
    fi

    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context passwords — show generated credentials
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_passwords() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"

    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    # try summary.txt first, then passwords.env
    local summary="$config_dir/summary.txt"
    local passwords="$config_dir/passwords.env"

    if [[ -f "$summary" ]]; then
        _r42_print_section "credentials summary"
        cat "$summary"
    elif [[ -f "$passwords" ]]; then
        _r42_print_section "passwords"
        cat "$passwords"
    else
        _r42_print_fail "no summary.txt or passwords.env found in $config_dir"
        _r42_print_warning "credentials may not have been generated yet"
    fi
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context ssh — quick ssh to a VM by partial name
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_ssh() {
    local pattern="$1"

    if [[ -z "$pattern" ]]; then
        _r42_print_fail "usage: range42-context ssh <hostname-pattern>"
        echo "  example: range42-context ssh wazuh"
        return 1
    fi

    # find matching host in main config + all included scenario configs
    # (grep does not follow Include directives, so we expand them manually)
    local ssh_config="${HOME}/.ssh/config"
    local matches
    matches=$(
        {
            grep "^Host r42\." "$ssh_config" 2>/dev/null
            grep '^Include ' "$ssh_config" 2>/dev/null \
                | grep 'config_range42' \
                | sed 's/^Include //' \
                | while IFS= read -r inc; do
                    grep "^Host r42\." "$inc" 2>/dev/null
                done
        } | awk '{print $2}' | grep -i "$pattern" | sort -u
    )

    if [[ -z "$matches" ]]; then
        _r42_print_fail "no host matching '$pattern' found"
        return 1
    fi

    local count
    count=$(echo "$matches" | wc -l)

    if [[ $count -gt 1 ]]; then
        _r42_print_warning "multiple hosts match '$pattern':"
        echo "$matches" | while read -r h; do
            echo "    $h"
        done
        echo ""
        echo "  be more specific or use: ssh <full-hostname>"
        return 1
    fi

    local host="$matches"
    _r42_print_step "connecting to $host"
    ssh "$host"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context deploy — run scenario setup script
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_deploy() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found"
        return 1
    fi

    local scenario_name
    scenario_name=$(basename "$(readlink -f "$scenario_dir")")
    local setup_script="$(readlink -f "$scenario_dir")/${scenario_name}.setup.sh"

    if [[ ! -f "$setup_script" ]]; then
        _r42_print_fail "setup script not found: $setup_script"
        return 1
    fi

    _r42_print_section "deploying scenario"
    _r42_flush_known_hosts "${RANGE42_ACTIVE_WORKSPACE:-}"
    _r42_print_step "running: $setup_script"
    echo ""

    cd "$(dirname "$setup_script")" && bash "$setup_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context deploy-vms — deploy VMs only (skip templates)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_deploy_vms() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found"
        return 1
    fi

    local scenario_name
    scenario_name=$(basename "$(readlink -f "$scenario_dir")")
    local script="$(readlink -f "$scenario_dir")/${scenario_name}.setup_vms_only.sh"

    if [[ ! -f "$script" ]]; then
        _r42_print_fail "script not found: $script"
        return 1
    fi

    _r42_print_section "deploying VMs only (skip templates)"
    _r42_flush_known_hosts "${RANGE42_ACTIVE_WORKSPACE:-}"
    _r42_print_step "running: $script"
    echo ""

    cd "$(dirname "$script")" && bash "$script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context delete — run scenario delete script
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_delete() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found"
        return 1
    fi

    local scenario_name
    scenario_name=$(basename "$(readlink -f "$scenario_dir")")
    local delete_script="$(readlink -f "$scenario_dir")/${scenario_name}.delete_all.sh"

    if [[ ! -f "$delete_script" ]]; then
        _r42_print_fail "script not found: $delete_script"
        return 1
    fi

    _r42_print_section "deleting scenario VMs"
    _r42_print_warning "this will destroy all VMs for the active scenario"
    _r42_print_step "running: $delete_script"
    echo ""

    cd "$(dirname "$delete_script")" && bash "$delete_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context reset — run scenario reset script
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_reset() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found"
        return 1
    fi

    local scenario_name
    scenario_name=$(basename "$(readlink -f "$scenario_dir")")
    local reset_script="$(readlink -f "$scenario_dir")/${scenario_name}.reset.setup.sh"

    if [[ ! -f "$reset_script" ]]; then
        _r42_print_fail "script not found: $reset_script"
        return 1
    fi

    _r42_print_section "resetting scenario (delete + reinstall)"
    _r42_print_warning "this will destroy and recreate all VMs"
    _r42_print_step "running: $reset_script"
    echo ""

    cd "$(dirname "$reset_script")" && bash "$reset_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context delete-vms — delete VMs only (keep templates)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_delete_vms() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found"
        return 1
    fi

    local scenario_name
    scenario_name=$(basename "$(readlink -f "$scenario_dir")")
    local script="$(readlink -f "$scenario_dir")/${scenario_name}.delete_vms_only.sh"

    if [[ ! -f "$script" ]]; then
        _r42_print_fail "script not found: $script"
        return 1
    fi

    _r42_print_section "deleting VMs only (keeping templates)"
    _r42_print_step "running: $script"
    echo ""

    cd "$(dirname "$script")" && bash "$script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# helpers — scenario manifest discovery
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

# Resolve the manifest path for the active scenario.
# Echoes the path on stdout, returns 0 on success, 1 on failure.
_r42_active_scenario_manifest() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace" >&2
        return 1
    fi

    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found" >&2
        return 1
    fi

    local manifest="$(readlink -f "$scenario_dir")/manifest/scenario_vms.json"
    if [[ ! -f "$manifest" ]]; then
        _r42_print_fail "manifest not found: $manifest" >&2
        _r42_print_warning "this scenario has no manifest yet (only blank_scenario_2_subnets has one for now)" >&2
        return 1
    fi

    echo "$manifest"
}

# Echo the active scenario name (basename of the symlink target).
_r42_active_scenario_name() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    [[ -z "$config_dir" ]] && return 1
    local scenario_dir="$config_dir/scenario"
    [[ ! -L "$scenario_dir" ]] && return 1
    basename "$(readlink -f "$scenario_dir")"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# helper — apply a devkit vm action to all scenario VMs (start/stop/pause/resume)
# usage: _r42_apply_to_scenario_vms <devkit_script> <label>
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_apply_to_scenario_vms() {
    local action_script="$1"
    local label="$2"
    local manifest scenario_name
    manifest=$(_r42_active_scenario_manifest) || return 1
    scenario_name=$(_r42_active_scenario_name) || return 1

    _r42_print_section "$label scenario VMs"
    _r42_print_step "scenario: $scenario_name"
    echo ""

    jq -c '.vms[] | {vm_id: .vm_id}' "$manifest" | "$action_script"

    echo ""
    _r42_print_check "$label done"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context start / stop / stop-force / pause / resume
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_start()      { _r42_apply_to_scenario_vms "proxmox_vm.vm_id.start.to.jsons.sh"      "starting"; }
_r42_stop()       { _r42_apply_to_scenario_vms "proxmox_vm.vm_id.stop.to.jsons.sh"       "stopping"; }
_r42_stop_force() { _r42_apply_to_scenario_vms "proxmox_vm.vm_id.stop_force.to.jsons.sh" "force-stopping"; }
_r42_pause()      { _r42_apply_to_scenario_vms "proxmox_vm.vm_id.pause.to.jsons.sh"      "pausing"; }
_r42_resume()     { _r42_apply_to_scenario_vms "proxmox_vm.vm_id.resume.to.jsons.sh"     "resuming"; }

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context snapshot — snapshot all VMs of the active scenario
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_snapshot() {
    local manifest scenario_name snap_name
    manifest=$(_r42_active_scenario_manifest) || return 1
    scenario_name=$(_r42_active_scenario_name) || return 1

    # Proxmox snapshot names: must start with [a-z], allow [a-z0-9_]
    # auto-generate if not provided: r42_<scenario>_YYYYMMDD_HHMMSS (lowercased, hyphens→_)
    local default_name
    default_name="r42_$(echo "$scenario_name" | tr '[:upper:]-' '[:lower:]_')_$(date +%Y%m%d_%H%M%S)"
    snap_name="${1:-$default_name}"

    _r42_print_section "snapshot scenario VMs"
    _r42_print_step "scenario : $scenario_name"
    _r42_print_step "snapshot : $snap_name"
    echo ""

    jq -c --arg name "$snap_name" --arg desc "range42 snapshot of $scenario_name" \
        '.vms[] | {vm_id: .vm_id, vm_snapshot_name: $name, vm_snapshot_description: $desc}' "$manifest" \
        | proxmox_snapshot_vm.vm_id.create_snapshot.to.jsons.sh

    echo ""
    _r42_print_check "snapshot created: $snap_name"
    echo "  revert with: range42-context revert $snap_name"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context revert — revert all VMs of the active scenario to a snapshot
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_revert() {
    local manifest scenario_name snap_name
    manifest=$(_r42_active_scenario_manifest) || return 1
    scenario_name=$(_r42_active_scenario_name) || return 1

    snap_name="${1:-}"
    if [[ -z "$snap_name" ]]; then
        _r42_print_fail "snapshot name required"
        echo "  usage: range42-context revert <snapshot_name>"
        echo "  list snapshots with: range42-context snapshot-list"
        return 1
    fi

    _r42_print_section "revert scenario VMs to snapshot"
    _r42_print_warning "this rolls back all scenario VMs to snapshot: $snap_name"
    _r42_print_step "scenario : $scenario_name"
    _r42_print_step "snapshot : $snap_name"
    echo ""

    jq -c --arg name "$snap_name" \
        '.vms[] | {vm_id: .vm_id, vm_snapshot_name: $name}' "$manifest" \
        | proxmox_snapshot_vm.vm_id.revert_snapshot.to.jsons.sh

    echo ""
    _r42_print_check "revert done"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context delete-everything — delete VMs + templates ACROSS ALL scenarios
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_delete_everything() {
    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"
    local playbooks_dir="$git_dir/range42-playbooks"

    if [[ ! -d "$playbooks_dir" ]]; then
        _r42_print_fail "range42-playbooks not found at: $playbooks_dir"
        return 1
    fi

    # collect all manifests (bash + zsh compatible — no mapfile)
    local manifests=()
    while IFS= read -r m; do
        [[ -n "$m" ]] && manifests+=("$m")
    done < <(find "$playbooks_dir/scenarios" -mindepth 3 -maxdepth 3 -name 'scenario_vms.json' -path '*/manifest/*' 2>/dev/null | sort)

    if [[ ${#manifests[@]} -eq 0 ]]; then
        _r42_print_fail "no scenario manifest found under $playbooks_dir/scenarios/*/manifest/"
        return 1
    fi

    _r42_print_section "DELETE EVERYTHING — cross-scenario nuke"
    _r42_print_warning "this will destroy ALL VMs + templates referenced by EVERY scenario manifest on this Proxmox"
    echo ""
    echo "  scenarios with a manifest:"
    for m in "${manifests[@]}"; do
        local scn
        scn=$(jq -r '.scenario' "$m")
        local n_vms n_tpl
        n_vms=$(jq '.vms | length' "$m")
        n_tpl=$(jq '.templates | length' "$m")
        echo "    - $scn  ($n_vms VMs, $n_tpl templates)"
    done
    echo ""
    _r42_print_warning "scenarios WITHOUT a manifest are skipped (their VMs will NOT be deleted)"
    echo ""

    # confirmation
    local reply
    printf "  type 'YES' to confirm cross-scenario nuke: "
    read -r reply
    if [[ "$reply" != "YES" ]]; then
        _r42_print_fail "aborted (you typed: '$reply')"
        return 1
    fi

    # accumulate all VM ids + IPs across all manifests (bash + zsh compatible)
    local all_ids=() all_ips=()
    for m in "${manifests[@]}"; do
        while IFS= read -r id; do
            [[ -n "$id" ]] && all_ids+=("$id")
        done < <(jq -r '.vms[].vm_id, .templates[].vm_id' "$m")
        while IFS= read -r ip; do
            [[ -n "$ip" ]] && all_ips+=("$ip")
        done < <(jq -r '.vms[].ip' "$m")
    done

    # dedup
    local dedup_ids=() dedup_ips=()
    while IFS= read -r v; do [[ -n "$v" ]] && dedup_ids+=("$v"); done < <(printf '%s\n' "${all_ids[@]}" | sort -u)
    while IFS= read -r v; do [[ -n "$v" ]] && dedup_ips+=("$v"); done < <(printf '%s\n' "${all_ips[@]}" | sort -u)
    all_ids=("${dedup_ids[@]}")
    all_ips=("${dedup_ips[@]}")

    local id_regex
    id_regex=$(printf '|%s' "${all_ids[@]}" | sed 's/^|//')

    echo ""
    _r42_print_step "stopping and deleting ${#all_ids[@]} VMs/templates ..."
    local _vm_list_json
    _vm_list_json=$(proxmox_vm.list.to.jsons.sh 2>&1 | grep '"vm_id":[0-9]')
    if [ -z "$_vm_list_json" ]; then
        _r42_print_fail "proxmox_vm.list.to.jsons.sh returned no VM data (no vm_id lines) — aborting nuke"
        _r42_print_warning "output: ${_vm_list_json[1,200]}"
        return 1
    fi
    echo "$_vm_list_json" | jq -c | grep -E "\"vm_id\":($id_regex)([^0-9]|\$)" | proxmox_vm.vm_id.stop_force.to.jsons.sh
    echo "$_vm_list_json" | jq -c | grep -E "\"vm_id\":($id_regex)([^0-9]|\$)" | proxmox_vm.vm_id.delete.to.jsons.sh

    echo ""
    _r42_print_step "cleaning ${#all_ips[@]} known_hosts entries ..."
    for ip in "${all_ips[@]}"; do
        ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$ip" >/dev/null 2>&1 && echo "  - $ip"
    done

    echo ""
    _r42_print_check "cross-scenario nuke complete"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# catalog-try helpers (used by `range42-context catalog-try <path>`)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

# Resolve a logical catalog path (e.g. `docker/_ctf/hello`) to an absolute path
# under range42-catalog/.
#
# The logical path skips the numbered layer prefix : the operator types
# `docker/_ctf/hello` instead of `03_container_layer/docker/_ctf/hello`. This
# function searches all `NN_<x>_layer/` directories for the first key and
# returns the matching absolute path.
#
# Usage: abs_path=$(_r42_catalog_resolve_path "docker/_ctf/hello")
#
# Returns 0 + abs path on stdout on success, 1 + error on stderr otherwise.
# Validation : final dir must exist and contain at least one of compose.yml,
# docker-compose.yml, or Makefile (otherwise not a deployable element).
_r42_catalog_resolve_path() {
    local input_path="$1"
    if [[ -z "$input_path" ]]; then
        _r42_print_fail "usage: _r42_catalog_resolve_path <path>" >&2
        return 1
    fi

    local catalog_root="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42-catalog"
    if [[ ! -d "$catalog_root" ]]; then
        _r42_print_fail "range42-catalog not found at $catalog_root" >&2
        return 1
    fi

    # Split input into first component (layer key) + rest
    local first="${input_path%%/*}"
    local rest="${input_path#*/}"
    if [[ "$first" == "$input_path" ]]; then
        rest=""
    fi

    # Find which numbered layer contains the first component as a subdir
    local matches=()
    local layer_dir
    for layer_dir in "$catalog_root"/*/; do
        layer_dir="${layer_dir%/}"
        local layer_name
        layer_name=$(basename "$layer_dir")
        # Only consider canonical numbered layer dirs (NN_<x>_layer)
        [[ "$layer_name" =~ ^[0-9]+_.*_layer$ ]] || continue
        if [[ -d "$layer_dir/$first" ]]; then
            matches+=("$layer_dir/$first")
        fi
    done

    if [[ ${#matches[@]} -eq 0 ]]; then
        _r42_print_fail "no catalog layer contains '$first'" >&2
        echo "  Available layer keys :" >&2
        for layer_dir in "$catalog_root"/*/; do
            layer_dir="${layer_dir%/}"
            local lname
            lname=$(basename "$layer_dir")
            [[ "$lname" =~ ^[0-9]+_.*_layer$ ]] || continue
            local sub
            for sub in "$layer_dir"/*/; do
                [[ -d "$sub" ]] && echo "    $(basename "$sub")  (in $lname)" >&2
            done
        done
        return 1
    fi

    if [[ ${#matches[@]} -gt 1 ]]; then
        _r42_print_fail "ambiguous : '$first' is in multiple layers" >&2
        local m
        for m in "${matches[@]}"; do echo "    $m" >&2; done
        return 1
    fi

    # Single layer match - construct the full target path
    local full_path="${matches[0]}"
    if [[ -n "$rest" ]]; then
        full_path="${full_path}/${rest}"
    fi

    # Verify the full path exists
    if [[ ! -e "$full_path" ]]; then
        _r42_print_fail "path not found : $full_path" >&2
        local parent
        parent=$(dirname "$full_path")
        if [[ -d "$parent" ]]; then
            echo "  Candidates under $parent :" >&2
            local c
            for c in "$parent"/*/; do
                [[ -d "$c" ]] && echo "    $(basename "$c")" >&2
            done
        fi
        return 1
    fi

    if [[ ! -d "$full_path" ]]; then
        _r42_print_fail "not a directory : $full_path" >&2
        return 1
    fi

    # Verify it's a deployable element (has at least one of compose.yml, docker-compose.yml, Makefile)
    if [[ ! -f "$full_path/compose.yml" ]] && \
       [[ ! -f "$full_path/docker-compose.yml" ]] && \
       [[ ! -f "$full_path/Makefile" ]]; then
        _r42_print_fail "not a deployable element : $full_path" >&2
        echo "  Missing : at least one of compose.yml, docker-compose.yml, or Makefile" >&2
        echo "  Subdirectories under this path (try a deeper match ?) :" >&2
        local c
        for c in "$full_path"/*/; do
            [[ -d "$c" ]] && echo "    $(basename "$c")" >&2
        done
        return 1
    fi

    # Resolution OK - emit absolute path on stdout
    echo "$full_path"
    return 0
}

# Read a single scalar value from a catalog_try.yml file (simple grep, no full YAML parsing).
# Usage : _r42_catalog_try_yml_get <yml_file> <key> [<default>]
_r42_catalog_try_yml_get() {
    local yml="$1" key="$2" default="${3:-}"
    [[ ! -f "$yml" ]] && { echo "$default" ; return ; }
    local val
    val=$(grep -E "^${key}:" "$yml" 2>/dev/null | sed -E "s/^${key}:[[:space:]]*//" | sed -E 's/^"(.*)"$/\1/' | head -1)
    if [[ -z "$val" ]] ; then
        echo "$default"
    else
        echo "$val"
    fi
}

# Main orchestrator : `range42-context catalog-try <path>`.
# Overwrites the catalog_try test VM, deploys a single catalog element on it,
# and runs a smoke check based on the element's optional catalog_try.yml.
#
# Usage : _r42_catalog_try <path>
#   <path> : logical catalog path (e.g. docker/_ctf/hello)
#
# Requires : active scenario = catalog_try (range42-context use <codename> catalog_try first).
_r42_catalog_try() {
    local path="$1"
    if [[ -z "$path" ]]; then
        _r42_print_fail "usage: range42-context catalog-try <path>"
        echo "  example : range42-context catalog-try docker/_ctf/hello" >&2
        return 1
    fi

    # 1. Resolve logical path to absolute catalog element dir
    local element_abs_path
    element_abs_path=$(_r42_catalog_resolve_path "$path") || return 1
    local element_name
    element_name=$(basename "$element_abs_path")

    # 2. Verify active scenario is catalog_try
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace"
        echo "  Switch with : range42-context use <codename> catalog_try" >&2
        return 1
    fi
    local active_scenario
    active_scenario=$(_r42_active_scenario_name 2>/dev/null) || {
        _r42_print_fail "could not resolve active scenario"
        return 1
    }
    if [[ "$active_scenario" != "catalog_try" ]]; then
        _r42_print_fail "active scenario is '$active_scenario', not 'catalog_try'"
        echo "  Switch with : range42-context use <codename> catalog_try" >&2
        return 1
    fi

    # 3. Read optional catalog_try.yml for smoke check config (defaults if missing)
    local catalog_try_yml="$element_abs_path/catalog_try.yml"
    local ct_mode ct_port ct_endpoint ct_init_timeout ct_exit_signature
    ct_mode=$(_r42_catalog_try_yml_get "$catalog_try_yml" "catalog_try_mode" "service")
    ct_port=$(_r42_catalog_try_yml_get "$catalog_try_yml" "catalog_try_port" "")
    ct_endpoint=$(_r42_catalog_try_yml_get "$catalog_try_yml" "catalog_try_endpoint" "/")
    ct_init_timeout=$(_r42_catalog_try_yml_get "$catalog_try_yml" "catalog_try_init_timeout" "60")
    ct_exit_signature=$(_r42_catalog_try_yml_get "$catalog_try_yml" "catalog_try_exit_signature" "")
    # Validate init_timeout is numeric (fall back to 60 if not)
    if ! [[ "$ct_init_timeout" =~ ^[0-9]+$ ]]; then
        _r42_print_warning "catalog_try_init_timeout '${ct_init_timeout}' is not a valid integer, defaulting to 60s"
        ct_init_timeout=60
    fi
    # Clamp init_timeout to max 600s (C.19)
    if [[ "$ct_init_timeout" -gt 600 ]]; then
        _r42_print_warning "catalog_try_init_timeout clamped from ${ct_init_timeout}s to 600s (max)"
        ct_init_timeout=600
    fi
    # Validate port is numeric if present (fall back to L1 if not)
    if [[ -n "$ct_port" ]] && ! [[ "$ct_port" =~ ^[0-9]+$ ]]; then
        _r42_print_warning "catalog_try_port '${ct_port}' is not a valid port number, falling back to L1 smoke check"
        ct_port=""
    fi

    # 4. Read VM allocation from scenario manifest
    local manifest
    manifest=$(_r42_active_scenario_manifest) || return 1
    local vm_ip vm_id vm_name vm_ssh
    vm_ip=$(jq -r '.vms[0].ip' "$manifest")
    vm_id=$(jq -r '.vms[0].vm_id' "$manifest")
    vm_name=$(jq -r '.vms[0].vm_name' "$manifest")
    vm_ssh="r42.${vm_name}"

    # 5. Confirmation prompt
    _r42_print_section "catalog-try : $path"
    _r42_print_step "Element       : $element_abs_path"
    _r42_print_step "Mode          : $ct_mode"
    if [[ "$ct_mode" == "service" && -n "$ct_port" ]]; then
        _r42_print_step "Smoke check   : curl http://${vm_ip}:${ct_port}${ct_endpoint}  (timeout ${ct_init_timeout}s)"
    elif [[ "$ct_mode" == "oneshot" && -n "$ct_exit_signature" ]]; then
        _r42_print_step "Smoke check   : grep '${ct_exit_signature}' in container output"
    else
        _r42_print_step "Smoke check   : L1 fallback (no contract declared)"
    fi
    _r42_print_step "Test VM       : ${vm_ssh}  (IP ${vm_ip}, VMID ${vm_id})"
    _r42_print_warning "This will DESTROY VM ${vm_id} and redeploy it fresh."
    read -r -p "  Continue ? [y/N] " response
    if [[ "$response" != "y" && "$response" != "Y" ]]; then
        echo "  Aborted."
        return 1
    fi

    # 6. Flush known_hosts for the test VM IP (avoid SSH host key collision)
    ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$vm_ip" >/dev/null 2>&1 || true

    # 7. Destroy previous test VM
    _r42_print_section "destroying previous test VM"
    _r42_delete_vms || { _r42_print_fail "delete_vms failed" ; return 1 ; }

    # 8. Redeploy fresh VM with Docker baseline
    _r42_print_section "redeploying test VM"
    _r42_deploy_vms || { _r42_print_fail "deploy_vms failed" ; return 1 ; }

    # 9. rsync element to the VM
    _r42_print_section "rsync element to test VM"
    local remote_dir="/home/alice/catalog-try-element"
    if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "$vm_ssh" "rm -rf ${remote_dir} && mkdir -p ${remote_dir}" ; then
        _r42_print_fail "cannot reach test VM via SSH (${vm_ssh})"
        return 1
    fi
    if ! rsync -a --delete "${element_abs_path}/" "${vm_ssh}:${remote_dir}/" ; then
        _r42_print_fail "rsync of element failed"
        return 1
    fi
    _r42_print_check "element rsynced to ${vm_ssh}:${remote_dir}"

    # 10. Run the element on the VM
    _r42_print_section "running element on test VM"
    local run_cmd
    if [[ -f "${element_abs_path}/Makefile" ]]; then
        # C.21 : Makefile wins if present
        _r42_print_step "Makefile detected -> running 'make up'"
        run_cmd="cd ${remote_dir} && make up"
    elif [[ "$ct_mode" == "oneshot" ]]; then
        _r42_print_step "oneshot mode -> docker compose up (no -d, captures output)"
        run_cmd="cd ${remote_dir} && docker compose up --abort-on-container-exit"
    else
        _r42_print_step "service mode -> docker compose up -d (detached)"
        run_cmd="cd ${remote_dir} && docker compose up -d"
    fi
    local run_log="/tmp/catalog-try-${element_name}-run.log"
    ssh -o BatchMode=yes -o ConnectTimeout=10 "$vm_ssh" "$run_cmd" 2>&1 | tee "$run_log"
    local ssh_rc=${PIPESTATUS[0]}
    if [[ "$ssh_rc" -ne 0 ]]; then
        _r42_print_fail "run failed (ssh exit ${ssh_rc}) - log saved at ${run_log}"
        return 1
    fi

    # 11. Smoke check based on mode + contract
    _r42_print_section "smoke check"
    if [[ "$ct_mode" == "oneshot" ]]; then
        if [[ -n "$ct_exit_signature" ]]; then
            local logs
            logs=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$vm_ssh" "cd ${remote_dir} && docker compose logs 2>&1")
            if echo "$logs" | grep -q "$ct_exit_signature" ; then
                _r42_print_check "PASS : signature '${ct_exit_signature}' found in container output"
            else
                _r42_print_fail "FAIL : signature '${ct_exit_signature}' NOT found in output"
                echo "----- container logs -----" >&2
                echo "$logs" >&2
                echo "--------------------------" >&2
                return 1
            fi
        else
            _r42_print_check "L1 PASS : container ran without runtime error (no exit_signature declared)"
        fi
    else
        # service mode
        if [[ -n "$ct_port" ]]; then
            local url="http://${vm_ip}:${ct_port}${ct_endpoint}"
            _r42_print_step "polling ${url}  (max ${ct_init_timeout}s)"
            local elapsed=0
            local step=5
            local ok=false
            while [[ "$elapsed" -lt "$ct_init_timeout" ]]; do
                if curl -fsS --max-time 5 "$url" >/dev/null 2>&1 ; then
                    ok=true
                    break
                fi
                sleep "$step"
                elapsed=$((elapsed + step))
                printf "    waited %ds / %ds ...\n" "$elapsed" "$ct_init_timeout"
            done
            if $ok ; then
                _r42_print_check "PASS : ${url} responded 200 OK after ${elapsed}s"
            else
                _r42_print_fail "FAIL : ${url} not reachable within ${ct_init_timeout}s"
                echo "----- compose logs (tail 50) -----" >&2
                ssh -o BatchMode=yes -o ConnectTimeout=10 "$vm_ssh" "cd ${remote_dir} && docker compose logs --tail 50" >&2
                echo "----------------------------------" >&2
                return 1
            fi
        else
            # L1 fallback : check docker ps shows at least one container
            local ps_out
            ps_out=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$vm_ssh" "docker ps --format '{{.Names}} {{.Status}}'")
            if [[ -n "$ps_out" ]] ; then
                _r42_print_check "L1 PASS : container(s) running"
                echo "$ps_out"
            else
                _r42_print_fail "L1 FAIL : no container visible in docker ps"
                return 1
            fi
        fi
    fi

    # 12. Print VM IP for inspection
    _r42_print_section "done"
    _r42_print_step "Test VM kept up for inspection :"
    _r42_print_step "  range42-context ssh ${vm_ssh}"
    _r42_print_step "  IP : ${vm_ip}"
    _r42_print_step "  Element rsynced at : ${remote_dir}  (on the VM)"
    _r42_print_step "Re-run with : range42-context catalog-try ${path}  (will overwrite)"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context init — launch the setup wizard from anywhere
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_init() {
    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"
    local init_script=""
    local search_paths=(
        "${git_dir%/}/range42/range42-init.py"
        "${git_dir%/}/range42-init.py"
    )
    for p in "${search_paths[@]}"; do
        if [[ -f "$p" ]]; then
            init_script="$p"
            break
        fi
    done

    if [[ -z "$init_script" ]]; then
        _r42_print_fail "range42-init.py not found"
        _r42_print_warning "searched:"
        for p in "${search_paths[@]}"; do
            _r42_print_warning "  $p"
        done
        return 1
    fi

    python3 "$init_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context debug — toggle verbose/skip output in ansible.cfg
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_debug() {
    # resolve ansible.cfg path:
    #   1. ANSIBLE_CONFIG (exported by range42-context use)
    #   2. RANGE42_GITDIR__ROOT_DIR/range42/ansible.cfg (custom install path from wizard)
    #   3. $HOME/range42/range42/ansible.cfg (default fallback)
    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"
    local cfg="${ANSIBLE_CONFIG:-${git_dir%/}/range42/ansible.cfg}"

    if [[ ! -f "$cfg" ]]; then
        _r42_print_fail "ansible.cfg not found: $cfg"
        return 1
    fi

    # check current state — if stdout_callback is active (not commented), we're in clean mode
    if grep -q '^stdout_callback = no_skipped' "$cfg"; then
        # switch to debug mode — comment out the no_skipped lines
        sed -i 's/^stdout_callback = no_skipped/# stdout_callback = no_skipped/' "$cfg"
        sed -i 's/^callback_plugins = callback_plugins/# callback_plugins = callback_plugins/' "$cfg"
        _r42_print_check "debug mode ON — skipped tasks will be visible"
    else
        # switch to clean mode — uncomment the no_skipped lines
        sed -i 's/^# stdout_callback = no_skipped/stdout_callback = no_skipped/' "$cfg"
        sed -i 's/^# callback_plugins = callback_plugins/callback_plugins = callback_plugins/' "$cfg"
        _r42_print_check "debug mode OFF — skipped tasks hidden"
    fi
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context help
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_help() {
    local C="\033[1;34m"  # category color (blue)
    local N="\033[1;37m"  # command name (white bold)
    local D="\033[0;90m"  # description (gray)
    local R="\033[0m"     # reset

    echo ""
    printf "  ${N}usage:${R} range42-context <command>\n"
    echo ""
    printf "  ${C}workspace${R}\n"
    printf "    ${N}list${R}                           ${D}list available workspaces${R}\n"
    printf "    ${N}current${R}                        ${D}show active workspace${R}\n"
    printf "    ${N}use${R} <codename> <scenario>      ${D}switch to a workspace${R}\n"
    printf "    ${N}status${R}                         ${D}check workspace health${R}\n"
    printf "    ${N}init${R}                           ${D}launch setup wizard${R}\n"
    echo ""
    printf "  ${C}navigation${R}\n"
    printf "    ${N}cd config${R}                      ${D}go to workspace config directory${R}\n"
    printf "    ${N}cd scenario${R}                    ${D}go to scenario playbooks directory${R}\n"
    printf "    ${N}cd secrets${R}                     ${D}go to vault/secrets directory${R}\n"
    echo ""
    printf "  ${C}operations${R}\n"
    printf "    ${N}deploy${R}                         ${D}run full scenario setup (templates + VMs)${R}\n"
    printf "    ${N}deploy-vms${R}                     ${D}deploy VMs only (skip templates)${R}\n"
    printf "    ${N}delete${R}                         ${D}delete all scenario VMs + templates${R}\n"
    printf "    ${N}delete-vms${R}                     ${D}delete VMs only (keep templates)${R}\n"
    printf "    ${N}delete-everything${R}              ${D}delete ALL VMs+templates across ALL scenarios (cross-scenario)${R}\n"
    printf "    ${N}reset${R}                          ${D}delete + recreate all VMs${R}\n"
    printf "    ${N}ssh-reload${R}                     ${D}reload SSH keys for active workspace${R}\n"
    echo ""
    printf "  ${C}lifecycle (all VMs of active scenario)${R}\n"
    printf "    ${N}start${R}                          ${D}start all scenario VMs${R}\n"
    printf "    ${N}stop${R}                           ${D}graceful shutdown of all scenario VMs${R}\n"
    printf "    ${N}stop-force${R}                     ${D}force stop all scenario VMs${R}\n"
    printf "    ${N}pause${R}                          ${D}pause all scenario VMs${R}\n"
    printf "    ${N}resume${R}                         ${D}resume all paused scenario VMs${R}\n"
    printf "    ${N}snapshot${R} [name]                ${D}snapshot all scenario VMs (auto-named if not provided)${R}\n"
    printf "    ${N}revert${R} <name>                  ${D}revert all scenario VMs to a snapshot${R}\n"
    echo ""
    printf "  ${C}info${R}\n"
    printf "    ${N}inventory${R}                      ${D}show ansible inventory tree${R}\n"
    printf "    ${N}passwords${R}                      ${D}show generated credentials${R}\n"
    printf "    ${N}ssh${R} <pattern>                  ${D}quick ssh to a VM by name${R}\n"
    printf "    ${N}debug${R}                          ${D}toggle verbose output (show/hide skipped tasks)${R}\n"
    printf "    ${N}help${R}                           ${D}show this help${R}\n"
    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# main entry point — range42-context function
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

range42-context() {

    local cmd="${1:-help}"
    shift 2>/dev/null

    case "$cmd" in
        list|ls)        _r42_list ;;
        current)        _r42_current ;;
        use)            _r42_use "$@" ;;
        status)         _r42_status ;;
        init)           _r42_init ;;
        deploy)             _r42_deploy ;;
        deploy-vms)         _r42_deploy_vms ;;
        delete)             _r42_delete ;;
        delete-vms)         _r42_delete_vms ;;
        delete-everything)  _r42_delete_everything ;;
        reset)              _r42_reset ;;
        start)              _r42_start ;;
        stop)               _r42_stop ;;
        stop-force)         _r42_stop_force ;;
        pause)              _r42_pause ;;
        resume)             _r42_resume ;;
        snapshot)           _r42_snapshot "$@" ;;
        revert)             _r42_revert "$@" ;;
        ssh-reload)     _r42_ssh_reload ;;
        inventory|inv)  _r42_inventory ;;
        passwords|pw)   _r42_passwords ;;
        ssh)            _r42_ssh "$@" ;;
        cd)             _r42_cd "$@" ;;
        debug)          _r42_debug ;;
        catalog-try)    _r42_catalog_try "$@" ;;
        help|--help|-h) _r42_help ;;
        *)
            _r42_print_fail "unknown command: $cmd"
            _r42_help
            return 1
            ;;
    esac
}
