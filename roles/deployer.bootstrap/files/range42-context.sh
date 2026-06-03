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

    local scenario_target
    if [[ -n "$ZSH_VERSION" ]]; then
        scenario_target="${scenario_link:A}"
    else
        scenario_target=$(readlink -f "$scenario_link") || return 0
    fi
    local manifest="${scenario_target}/manifest/scenario_vms.json"
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
# helpers for vault-backed SSH key auto-unlock (used by _r42_ssh_reload)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

# _r42_yaml_get — extract a top-level scalar field from YAML on stdin via yq.
# Returns empty string if the field is absent or null.
# usage : echo "$yaml" | _r42_yaml_get <field_name>
_r42_yaml_get() {
    local field="$1"
    yq -r ".${field} // \"\""
}

# _r42_passphrase_field_for_key — map an SSH key file path to the YAML field
# name in the vault that holds its passphrase. Echoes the field name on match,
# empty otherwise.
# usage : _r42_passphrase_field_for_key <key_file_path>
_r42_passphrase_field_for_key() {
    local keyfile="$1"
    case "$keyfile" in
        *ssh_cli.root)       echo "ssh_passphrase_px_root" ;;
        *ssh_cli.jump_user)  echo "ssh_passphrase_px_jump" ;;
        *deployer-key_alice) echo "ssh_passphrase_deployer_admin" ;;
        *student-key_bob_*)  echo "ssh_passphrase_student_user_extra_all" ;;
        *student-key_bob)    echo "ssh_passphrase_student_user" ;;
        *)                   echo "" ;;
    esac
}

# _r42_ssh_add_with_passphrase — non-interactive ssh-add via SSH_ASKPASS.
# Creates a one-shot askpass tempfile script that prints $SSH_ASKPASS_PASSWORD,
# invokes ssh-add with SSH_ASKPASS_REQUIRE=force and stdin from /dev/null so
# ssh-add cannot fall back to /dev/tty, then cleans up the tempfile.
# Returns ssh-add's exit code (0 on success, non-zero on bad passphrase / etc).
# usage : _r42_ssh_add_with_passphrase <key_file_path> <passphrase>
_r42_ssh_add_with_passphrase() {
    local keyfile="$1"
    local passphrase="$2"
    local askpass_script rc

    askpass_script=$(mktemp -t r42-askpass-XXXXXX.sh) || return 1
    chmod 700 "$askpass_script"
    printf '#!/bin/sh\nprintf "%%s" "$SSH_ASKPASS_PASSWORD"\n' > "$askpass_script"

    SSH_ASKPASS="$askpass_script" \
    SSH_ASKPASS_PASSWORD="$passphrase" \
    SSH_ASKPASS_REQUIRE=force \
        ssh-add "$keyfile" </dev/null >/dev/null 2>&1
    rc=$?

    rm -f "$askpass_script"
    return $rc
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

    # decrypt the vault once for passphrase lookup. On any failure (missing
    # vault_pass.txt, missing vault file, decrypt error), $vault_content stays
    # empty and the per-key loop falls back to interactive ssh-add. No abort.
    local vault_file vault_pass_file vault_content=""
    vault_file="${RANGE42_CONFIG__ROOT_DIR%/}/secrets/default_vault.yml"
    vault_pass_file="${RANGE42_VAULT_PASSWORD_FILE:-}"

    if [[ -n "$vault_pass_file" && -f "$vault_pass_file" && -f "$vault_file" ]]; then
        vault_content=$(ansible-vault view "$vault_file" \
            --vault-password-file "$vault_pass_file" 2>/dev/null) \
            || vault_content=""
    fi

    if [[ -z "$vault_content" && "$verbose" == "-v" ]]; then
        _r42_print_warning "vault not readable - ssh-add will prompt interactively for passphrase-protected keys"
    fi

    # parse active ssh config for IdentityFile entries
    # FIX P4: trim leading whitespace from IdentityFile paths
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

                    # try passphrase lookup from vault first
                    local field="" passphrase=""
                    if [[ -n "$vault_content" ]]; then
                        field=$(_r42_passphrase_field_for_key "$identity_file")
                        if [[ -n "$field" ]]; then
                            passphrase=$(echo "$vault_content" | _r42_yaml_get "$field")
                        fi
                    fi

                    if [[ -n "$passphrase" ]]; then
                        # non-interactive via SSH_ASKPASS ; fall back to /dev/tty
                        # if the vault passphrase does not match the key (desync).
                        if ! _r42_ssh_add_with_passphrase "$identity_file" "$passphrase"; then
                            ssh-add "$identity_file" </dev/tty 2>/dev/null
                        fi
                    else
                        # vault unreadable, field absent, or empty passphrase :
                        # plain ssh-add. Loads unprotected keys silently, prompts
                        # for protected ones via /dev/tty (legacy behavior).
                        ssh-add "$identity_file" </dev/tty 2>/dev/null
                    fi
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

    #### mirror the .zshrc workspace block : add devkit to PATH + gdk alias.
    #### These two lines live in the per-workspace block of .zshrc (see role
    #### workspace.credentials/tasks/03_deploy_sourced_env.yml) so they fire on a
    #### fresh shell. Without mirroring them here, `range42-context use` from an
    #### already-loaded shell would leave devkit out of PATH until the user spawns
    #### a new zsh — confusing UX.
    if [[ -n "$RANGE42_ANSIBLE_ROLES__DEVKITS_DIR" ]]; then
        case ":$PATH:" in
            *":$RANGE42_ANSIBLE_ROLES__DEVKITS_DIR:"*) ;;
            *) export PATH="$PATH:$RANGE42_ANSIBLE_ROLES__DEVKITS_DIR" ;;
        esac
        alias gdk="cd $RANGE42_ANSIBLE_ROLES__DEVKITS_DIR"
        _r42_print_step "devkit added to PATH (idempotent) + gdk alias defined"
    fi

    #### update secrets symlinks in git repos to point to the active workspace

    local git_dir="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}"
    local devkit_secrets="${git_dir%/}/range42-ansible_roles-debug-devkit/secrets"
    local playbooks_secrets="${git_dir%/}/range42-playbooks/scenarios/${scenario}/secrets"

    if [[ -d "${git_dir%/}/range42-ansible_roles-debug-devkit" ]]; then
        ln -sfn "$config_dir/secrets" "$devkit_secrets"
        _r42_print_step "updated secrets symlink in devkit → $target"
    else
        _r42_print_warning "range42-ansible_roles-debug-devkit not found at ${git_dir%/}/range42-ansible_roles-debug-devkit"
        _r42_print_warning "  -> devkit scripts (proxmox_vm.*.sh) will not work in this shell"
    fi
    if [[ -d "${git_dir%/}/range42-playbooks/scenarios/${scenario}" ]]; then
        ln -sfn "$config_dir/secrets" "$playbooks_secrets"
        _r42_print_step "updated secrets symlink in playbooks → $target"
    else
        _r42_print_warning "scenario '${scenario}' not found in range42-playbooks (${git_dir%/}/range42-playbooks/scenarios/${scenario})"
        _r42_print_warning "  -> ansible-playbook calls will fail ; verify the scenario name or pull range42-playbooks"
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
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local scenario_name="${scenario_target##*/}"
    local setup_script="${scenario_target}/${scenario_name}.setup.sh"

    if [[ ! -f "$setup_script" ]]; then
        _r42_print_fail "setup script not found: $setup_script"
        return 1
    fi

    _r42_print_section "deploying scenario"
    _r42_flush_known_hosts "${RANGE42_ACTIVE_WORKSPACE:-}"
    _r42_print_step "running: $setup_script"
    echo ""

    cd "$scenario_target" && bash "$setup_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context deploy-vms — deploy VMs only (skip templates)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_deploy_vms() {
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local scenario_name="${scenario_target##*/}"
    local script="${scenario_target}/${scenario_name}.setup_vms_only.sh"

    if [[ ! -f "$script" ]]; then
        _r42_print_fail "script not found: $script"
        return 1
    fi

    _r42_print_section "deploying VMs only (skip templates)"
    _r42_flush_known_hosts "${RANGE42_ACTIVE_WORKSPACE:-}"
    _r42_print_step "running: $script"
    echo ""

    cd "$scenario_target" && bash "$script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context delete — run scenario delete script
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_delete() {
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local scenario_name="${scenario_target##*/}"
    local delete_script="${scenario_target}/${scenario_name}.delete_all.sh"

    if [[ ! -f "$delete_script" ]]; then
        _r42_print_fail "script not found: $delete_script"
        return 1
    fi

    _r42_print_section "deleting scenario VMs"
    _r42_print_warning "this will destroy all VMs for the active scenario"
    _r42_print_step "running: $delete_script"
    echo ""

    cd "$scenario_target" && bash "$delete_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context reset — run scenario reset script
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_reset() {
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local scenario_name="${scenario_target##*/}"
    local reset_script="${scenario_target}/${scenario_name}.reset.setup.sh"

    if [[ ! -f "$reset_script" ]]; then
        _r42_print_fail "script not found: $reset_script"
        return 1
    fi

    _r42_print_section "resetting scenario (delete + reinstall)"
    _r42_print_warning "this will destroy and recreate all VMs"
    _r42_print_step "running: $reset_script"
    echo ""

    cd "$scenario_target" && bash "$reset_script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context delete-vms — delete VMs only (keep templates)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_delete_vms() {
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local scenario_name="${scenario_target##*/}"
    local script="${scenario_target}/${scenario_name}.delete_vms_only.sh"

    if [[ ! -f "$script" ]]; then
        _r42_print_fail "script not found: $script"
        return 1
    fi

    _r42_print_section "deleting VMs only (keeping templates)"
    _r42_print_step "running: $script"
    echo ""

    cd "$scenario_target" && bash "$script"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# helpers — scenario directory / manifest / name discovery
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

# Resolve the absolute directory of the active scenario (target of the
# $RANGE42_ACTIVE_CONFIG_DIR/scenario symlink).
# Echoes the path on stdout ; errors go to stderr ; returns 0/1.
#
# Uses zsh native ${var:A} when available — no external readlink dep, which has
# proved unreliable inside some freshly-sourced function call chains on the deployer.
# Falls back to readlink -f for bash callers.
_r42_active_scenario_dir() {
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace (RANGE42_ACTIVE_CONFIG_DIR is empty)" >&2
        return 1
    fi
    local scenario_dir="$config_dir/scenario"
    if [[ ! -L "$scenario_dir" ]]; then
        _r42_print_fail "scenario symlink not found: $scenario_dir" >&2
        return 1
    fi
    local target
    if [[ -n "$ZSH_VERSION" ]]; then
        target="${scenario_dir:A}"
    else
        target=$(readlink -f "$scenario_dir") || {
            _r42_print_fail "readlink -f failed on $scenario_dir" >&2
            return 1
        }
    fi
    if [[ -z "$target" ]]; then
        _r42_print_fail "resolved scenario target is empty for $scenario_dir" >&2
        return 1
    fi
    echo "$target"
}

# Echo the manifest path for the active scenario.
_r42_active_scenario_manifest() {
    local scenario_target
    scenario_target=$(_r42_active_scenario_dir) || return 1
    local manifest="${scenario_target}/manifest/scenario_vms.json"
    if [[ ! -f "$manifest" ]]; then
        _r42_print_fail "manifest not found: $manifest" >&2
        _r42_print_warning "this scenario has no manifest yet (only blank_scenario_2_subnets has one for now)" >&2
        return 1
    fi
    echo "$manifest"
}

# Echo the active scenario name (final path component of the symlink target).
_r42_active_scenario_name() {
    local target
    target=$(_r42_active_scenario_dir) || return 1
    echo "${target##*/}"
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
    echo "  list snapshots with: range42-context snapshot-list"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-context snapshot-list — list snapshots of all VMs of the active scenario
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42_snapshot_list() {
    local manifest scenario_name
    manifest=$(_r42_active_scenario_manifest) || return 1
    scenario_name=$(_r42_active_scenario_name) || return 1

    _r42_print_section "list snapshots of scenario VMs"
    _r42_print_step "scenario : $scenario_name"
    echo ""

    jq -c '.vms[] | {vm_id: .vm_id}' "$manifest" \
        | proxmox_snapshot_vm.vm_id.list_snapshot.to.jsons.sh

    echo ""
    _r42_print_check "snapshot listing done"
    echo "  revert with: range42-context revert <snapshot_name>"
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

    # Anchor on RANGE42_INVENTORY (set by the scenario env) so the resolver is not
    # restricted to a single catalog subtree. Falls back to $HOME/range42/range42-catalog.
    local catalog_root="${RANGE42_INVENTORY:-$HOME/range42/range42-catalog}"
    if [[ ! -d "$catalog_root" ]]; then
        _r42_print_fail "range42-catalog not found at $catalog_root (set RANGE42_INVENTORY)" >&2
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
        local layer_name="${layer_dir##*/}"
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
            local lname="${layer_dir##*/}"
            [[ "$lname" =~ ^[0-9]+_.*_layer$ ]] || continue
            local sub sname
            for sub in "$layer_dir"/*/; do
                sub="${sub%/}"
                sname="${sub##*/}"
                [[ -d "$sub" ]] && echo "    ${sname}  (in ${lname})" >&2
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
    # Note: zsh arrays are 1-indexed, bash 0-indexed. Iterate to grab the first
    # element in a shell-agnostic way (we know matches has exactly 1 element here).
    local full_path=""
    local _m
    for _m in "${matches[@]}"; do full_path="$_m"; break; done
    if [[ -n "$rest" ]]; then
        full_path="${full_path}/${rest}"
    fi

    # Verify the full path exists
    if [[ ! -e "$full_path" ]]; then
        _r42_print_fail "path not found : $full_path" >&2
        local parent="${full_path%/*}"
        if [[ -d "$parent" ]]; then
            echo "  Candidates under $parent :" >&2
            local c cname
            for c in "$parent"/*/; do
                c="${c%/}"
                cname="${c##*/}"
                [[ -d "$c" ]] && echo "    ${cname}" >&2
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
        local c cname
        for c in "$full_path"/*/; do
            c="${c%/}"
            cname="${c##*/}"
            [[ -d "$c" ]] && echo "    ${cname}" >&2
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

# List all catalog elements that can be run via `range42-context catalog-try`.
# Scans range42-catalog/NN_*_layer/.../ for directories that look deployable
# (compose.yml / docker-compose.yml / Makefile) and marks those carrying a
# `catalog_try.yml` contract as L2 (strict smoke) vs L1 (default fallback).
#
# Output is meant for the operator to discover what's runnable. Logical paths
# (with the NN_*_layer/ prefix stripped) are ready to copy-paste into a
# `range42-context catalog-try <path>` invocation.
#
# Optional args : two logical-path prefixes to scope the listing.
#   $1 = include_prefix : if set, keep only elements whose rel_path starts with it
#   $2 = exclude_prefix : if set, drop elements whose rel_path starts with it
# Both empty = list everything. Used by the dispatch to split admin vs non-admin
# without changing the underlying scan logic.
_r42_catalog_try_list() {
    hash -r 2>/dev/null || true

    local include_prefix="${1:-}"
    local exclude_prefix="${2:-}"

    local catalog_root="${RANGE42_INVENTORY:-$HOME/range42/range42-catalog}"
    if [[ ! -d "$catalog_root" ]]; then
        _r42_print_fail "range42-catalog not found at $catalog_root"
        _r42_print_step "set RANGE42_INVENTORY or activate a workspace : range42-context use <codename> <scenario>"
        return 1
    fi

    local scope_label=""
    if [[ -n "$include_prefix" ]]; then
        scope_label="only ${include_prefix}"
    elif [[ -n "$exclude_prefix" ]]; then
        scope_label="excluding ${exclude_prefix}"
    fi
    if [[ -n "$scope_label" ]]; then
        _r42_print_section "catalog elements compatible with catalog-try  (${scope_label})"
    else
        _r42_print_section "catalog elements compatible with catalog-try"
    fi
    _r42_print_step "catalog root : $catalog_root"
    echo ""

    # color codes : L2 = green (strict contract, "good"), L1 = yellow (fallback,
    # "ok but best-effort"). Plain reset at the end of each marker.
    local L2_COLOR='\033[1;32m'
    local L1_COLOR='\033[1;33m'
    local COLOR_RESET='\033[0m'

    local layer_re='^[0-9]+_.*_layer$'
    local count_l1=0 count_l2=0
    local layer layer_name elem rel_path

    for layer in "$catalog_root"/*/; do
        layer="${layer%/}"
        layer_name="${layer##*/}"
        [[ "$layer_name" =~ $layer_re ]] || continue

        # Find all dirs under this layer that look deployable. Use `find -type d`
        # then check for compose/Makefile presence per dir (simple, no trickery).
        # `-not -path '*/roles/*'` filters out ansible-role internals (e.g.
        # 02_ansible_layer/admin/roles/.../files) that may contain a compose.yml
        # as a template but are not catalog-try-deployable elements.
        while IFS= read -r elem; do
            if [[ -f "$elem/compose.yml" ]] || [[ -f "$elem/docker-compose.yml" ]] || [[ -f "$elem/Makefile" ]]; then
                # logical path : strip the layer dir prefix
                rel_path="${elem#${layer}/}"
                # Scope filters : include-prefix (positive) + exclude-prefix (negative).
                [[ -n "$include_prefix" && "$rel_path" != "$include_prefix"* ]] && continue
                [[ -n "$exclude_prefix" && "$rel_path" == "$exclude_prefix"* ]] && continue
                if [[ -f "$elem/catalog_try.yml" ]]; then
                    printf "    ${L2_COLOR}[L2]${COLOR_RESET}  %s\n" "$rel_path"
                    count_l2=$((count_l2 + 1))
                else
                    printf "    ${L1_COLOR}[L1]${COLOR_RESET}  %s\n" "$rel_path"
                    count_l1=$((count_l1 + 1))
                fi
            fi
        done < <(find "$layer" -mindepth 1 -type d -not -path '*/roles/*' 2>/dev/null | sort)
    done

    echo ""
    if [[ $((count_l1 + count_l2)) -eq 0 ]]; then
        if [[ -n "$scope_label" ]]; then
            _r42_print_warning "no deployable elements matched the scope (${scope_label}) under ${catalog_root}"
        else
            _r42_print_warning "no deployable elements found under ${catalog_root}"
            _r42_print_step "expected at least one directory containing compose.yml, docker-compose.yml, or Makefile"
            _r42_print_step "verify the catalog is properly cloned : ls -la ${catalog_root}"
        fi
        return 1
    fi

    # Counts with inline color markers matching the L2/L1 colors above.
    printf "    \033[34m➜\033[0m %d deployable elements  (${L2_COLOR}L2${COLOR_RESET}: %d, ${L1_COLOR}L1${COLOR_RESET}: %d)\n" \
        "$((count_l1 + count_l2))" "$count_l2" "$count_l1"

    _r42_print_section "legend"
    printf "    ${L2_COLOR}[L2]${COLOR_RESET}  catalog_try.yml present  - strict smoke check (signature grep or HTTP poll)\n"
    printf "    ${L1_COLOR}[L1]${COLOR_RESET}  no contract              - best-effort fallback (docker ps -a, any container)\n"
    echo ""
    _r42_print_step "run any : range42-context catalog-try <logical_path>"
}

# Convenience : list only admin-scoped docker elements (docker/admin/*).
_r42_catalog_try_list_admin() {
    _r42_catalog_try_list "docker/admin/" ""
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
    # IMPORTANT : do NOT name this local var "path" — zsh ties $PATH (string) to
    # $path (array). Declaring `local path="$1"` silently overwrites PATH in this
    # function's scope, breaking every external command (jq, ssh, basename, bash...).
    # See : zsh manual, typeset -T (tied parameters).
    local catalog_path="$1"
    if [[ -z "$catalog_path" ]]; then
        _r42_print_fail "usage: range42-context catalog-try <path>"
        echo "  example : range42-context catalog-try docker/_ctf/hello" >&2
        return 1
    fi

    # 1. Resolve logical path to absolute catalog element dir
    local element_abs_path
    element_abs_path=$(_r42_catalog_resolve_path "$catalog_path") || return 1
    local element_name="${element_abs_path##*/}"

    _r42_print_section "pre-flight"
    _r42_print_step "resolved element : ${element_abs_path}"

    # 2. Verify (and if needed, auto-switch to) a catalog_try workspace
    #
    # Auto-switch policy (strict same-codename) :
    #   - active workspace IS catalog_try   -> continue
    #   - active workspace IS NOT catalog_try but <codename>-catalog_try exists for
    #     the SAME codename                 -> prompt, then auto `range42-context use`
    #   - active workspace IS NOT catalog_try and <codename>-catalog_try is absent
    #                                       -> fail loud + suggest bootstrap (no
    #                                          auto-switch to OTHER codenames'
    #                                          catalog_try workspaces : the inventory,
    #                                          vault, and ssh config wouldn't match)
    local config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
    local active_scenario=""
    _r42_print_step "active config dir : ${config_dir:-<empty>}"

    # Stale env var recovery : if RANGE42_ACTIVE_CONFIG_DIR points to a dir
    # that no longer exists (e.g. the operator moved or deleted ~/range42.config
    # after the env was set, without re-sourcing the shell), treat as "no active
    # workspace" and fall through to the auto-detection logic below. Saves the
    # operator from having to manually `exec zsh` first.
    if [[ -n "$config_dir" ]] && [[ ! -d "$config_dir" ]]; then
        _r42_print_warning "RANGE42_ACTIVE_CONFIG_DIR points to a non-existent dir : ${config_dir}"
        _r42_print_step "(stale env var ; treating as no active workspace)"
        config_dir=""
    fi

    if [[ -z "$config_dir" ]]; then
        _r42_print_fail "no active workspace (RANGE42_ACTIVE_CONFIG_DIR is empty)"

        # Enumerate any catalog_try workspaces present locally — the auto-switch
        # decision below is keyed on how many we find.
        # zsh's default `nomatch` errors out on unmatched globs ; we enable
        # null_glob locally so an empty match expands to nothing instead.
        # `setopt local_options null_glob` is zsh-specific ; bash has no `setopt`
        # so the redirect + `|| true` makes the call safe (bash treats unmatched
        # globs as literal by default, which the `-d` check below filters out).
        setopt local_options null_glob 2>/dev/null || true
        local _ct_workspaces=() _ws_dir
        for _ws_dir in "$HOME/range42.config/"*-catalog_try ; do
            [[ -d "$_ws_dir" ]] || continue
            _ct_workspaces+=("${_ws_dir##*/}")
        done

        if [[ ${#_ct_workspaces[@]} -eq 1 ]]; then
            # Exactly one catalog_try workspace exists : safe to offer auto-activate.
            local target_workspace=""
            local _ws
            for _ws in "${_ct_workspaces[@]}"; do target_workspace="$_ws"; break; done
            local active_codename="${target_workspace%-catalog_try}"
            _r42_print_step "found exactly one catalog_try workspace : ${target_workspace}"
            printf "  activate %s and continue ? [Y/n] " "$target_workspace"
            local switch_reply
            read -r switch_reply
            if [[ "$switch_reply" != "" && "$switch_reply" != "y" && "$switch_reply" != "Y" ]]; then
                echo "  Aborted."
                return 1
            fi
            _r42_use "$active_codename" "catalog_try" || return 1
            # Refresh local state. active_scenario is intentionally set to the
            # constant : we know what we just activated, and the next check
            # `[[ -z "$active_scenario" ]]` below skips the redundant lookup.
            config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
            active_scenario="catalog_try"

        elif [[ ${#_ct_workspaces[@]} -gt 1 ]]; then
            # Multiple catalog_try workspaces : would have to pick a codename ;
            # refuse to guess (different codenames carry different Proxmox,
            # inventory, vault — wrong pick = subtle breakage).
            local _q_path="'${catalog_path//\'/\'\\\'\'}'"
            _r42_print_step "multiple catalog_try workspaces exist (cannot auto-pick) :"
            local _ws
            for _ws in "${_ct_workspaces[@]}" ; do
                printf "      %s\n" "$_ws" >&2
            done
            _r42_print_step "activate one : range42-context use <codename> catalog_try"
            _r42_print_step "then re-run  : range42-context catalog-try ${_q_path}"
            return 1

        elif [[ -d "$HOME/range42.config" ]] && [[ -n "$(ls -A "$HOME/range42.config" 2>/dev/null)" ]]; then
            # Some workspaces exist, but none for catalog_try : list + suggest
            # either activating an existing one or bootstrapping a catalog_try one.
            local _q_path="'${catalog_path//\'/\'\\\'\'}'"
            _r42_print_step "available workspaces in ~/range42.config/ (none are catalog_try) :"
            ls "$HOME/range42.config/" | sed 's/^/      /' >&2
            _r42_print_step "options :"
            _r42_print_step "  1) activate an existing : range42-context use <codename> <scenario>"
            _r42_print_step "  2) bootstrap a new catalog_try : python3 ${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42/range42-init.py --catalog-try ${_q_path}"
            return 1

        else
            # No workspaces at all : auto-launch the wizard with the catalog path
            # threaded through. The 2s wait gives the operator a chance to Ctrl+C
            # if the auto-bootstrap is not desired.
            _r42_print_step "no infrastructure configured yet (~/range42.config is empty)"
            local wizard_path="${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42/range42-init.py"
            if [[ ! -f "$wizard_path" ]]; then
                # Wizard not present : fall back to manual suggestion (with
                # defensive single-quote escape on catalog_path).
                local _q_path="'${catalog_path//\'/\'\\\'\'}'"
                _r42_print_fail "wizard not found at ${wizard_path}"
                _r42_print_step "clone range42 first, then run manually :"
                _r42_print_step "  cd ${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42 && python3 range42-init.py --catalog-try ${_q_path}"
                return 1
            fi
            echo ""
            echo ""
            _r42_print_step "launching wizard for first configuration ..."
            _r42_print_step "  (Ctrl+C now to abort)"
            echo ""
            echo ""
            sleep 2
            python3 "$wizard_path" --catalog-try "$catalog_path"
            return $?
        fi
    fi

    # Resolve active scenario unless we already set it (in the auto-activate path above).
    if [[ -z "$active_scenario" ]]; then
        active_scenario=$(_r42_active_scenario_name) || {
            local _q_path="'${catalog_path//\'/\'\\\'\'}'"
            _r42_print_fail "could not resolve active scenario (see error above)"
            echo "  Tried : ${config_dir}/scenario" >&2
            _r42_print_step "workspace appears corrupted ; re-bootstrap with the same element :"
            _r42_print_step "  cd ${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42 && python3 range42-init.py --catalog-try ${_q_path}"
            return 1
        }
    fi
    _r42_print_step "active scenario  : ${active_scenario}"

    if [[ "$active_scenario" != "catalog_try" ]]; then
        # Derive codename from the active workspace name. Workspace dir is
        # named "<codename>-<scenario>" (codenames may contain hyphens, so we
        # strip the trailing "-${active_scenario}" rather than splitting).
        local active_workspace="${config_dir##*/}"
        local active_codename="${active_workspace%-${active_scenario}}"
        local target_workspace="${active_codename}-catalog_try"
        local target_dir="$HOME/range42.config/${target_workspace}"

        if [[ -d "$target_dir" ]]; then
            _r42_print_warning "active scenario is '${active_scenario}', not 'catalog_try'"
            _r42_print_step "found existing workspace : ${target_workspace}"
            # %s format to defuse any % in $target_workspace (defensive ;
            # codenames are normally sanitized by the wizard).
            printf "  switch to %s and continue ? [Y/n] " "$target_workspace"
            local switch_reply
            read -r switch_reply
            if [[ "$switch_reply" != "" && "$switch_reply" != "y" && "$switch_reply" != "Y" ]]; then
                echo "  Aborted."
                return 1
            fi
            _r42_use "$active_codename" "catalog_try" || return 1
            # refresh local vars after the switch (config_dir + scenario changed)
            config_dir="${RANGE42_ACTIVE_CONFIG_DIR:-}"
            active_scenario="catalog_try"
        else
            # Defensive quote (same idiom as the "no workspace" branch above) :
            # protect catalog_path against shell-meta leaking into copy-paste suggestions.
            local _q_path="'${catalog_path//\'/\'\\\'\'}'"
            _r42_print_fail "active scenario is '${active_scenario}', and no catalog_try workspace exists for codename '${active_codename}'"
            _r42_print_step "options :"
            _r42_print_step "  1) bootstrap a catalog_try workspace via the wizard :"
            _r42_print_step "     cd ${RANGE42_GITDIR__ROOT_DIR:-$HOME/range42}/range42 && python3 range42-init.py --catalog-try ${_q_path}"
            _r42_print_step "  2) if you already created a catalog_try workspace, activate + re-run :"
            _r42_print_step "     range42-context use ${active_codename} catalog_try"
            _r42_print_step "     range42-context catalog-try ${_q_path}"
            # Info-only listing of catalog_try workspaces on OTHER codenames.
            # Never auto-switch to those (Proxmox API + inventory + vault would
            # mismatch the active infra context).
            # zsh `nomatch` would error on no-match : null_glob locally (no-op
            # in bash thanks to redirect + || true).
            setopt local_options null_glob 2>/dev/null || true
            local _other_ws _other_list=""
            for _other_ws in "$HOME/range42.config/"*-catalog_try ; do
                [[ -d "$_other_ws" ]] || continue
                local _other_name="${_other_ws##*/}"
                [[ "$_other_name" == "${target_workspace}" ]] && continue
                _other_list+="      ${_other_name}"$'\n'
            done
            if [[ -n "$_other_list" ]]; then
                _r42_print_warning "other catalog_try workspaces exist on different codenames (NOT auto-switched, mixing codenames is unsafe) :"
                printf "%s" "$_other_list" >&2
            fi
            return 1
        fi
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
    _r42_print_section "summary"
    _r42_print_step "Element       : ${element_name}"
    _r42_print_step "Catalog path  : ${catalog_path}"
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
    # Portable prompt (bash `read -p` is not zsh-compatible : -p means coprocess in zsh)
    printf '  Continue ? [y/N] '
    read -r response
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

    # 9-11. Deploy element to VM (copy + run + smoke) via Ansible playbook.
    # The playbook handles file transfer (ansible.builtin.copy / SFTP), docker
    # compose / make execution (become:true, no shell sudo), and the smoke check
    # (oneshot exit_signature grep / service HTTP polling via uri / L1 docker ps).
    # All visible in PLAY RECAP, debuggable as standard Ansible tasks.
    _r42_print_section "deploy element to test VM (copy + run + smoke)"
    local remote_dir="/home/alice/catalog-try-element"
    local scenario_dir
    scenario_dir=$(_r42_active_scenario_dir) || return 1
    local deploy_script="${scenario_dir}/catalog_try.element_deploy.sh"
    if [[ ! -f "$deploy_script" ]]; then
        _r42_print_fail "deploy script not found: ${deploy_script}"
        _r42_print_step "expected file from catalog_try scenario - pull latest range42-playbooks ?"
        return 1
    fi
    local use_makefile="false"
    [[ -f "${element_abs_path}/Makefile" ]] && use_makefile="true"
    if ! (
        cd "$scenario_dir" && \
        CATALOG_TRY_ELEMENT_SRC="$element_abs_path" \
        CATALOG_TRY_MODE="$ct_mode" \
        CATALOG_TRY_USE_MAKEFILE="$use_makefile" \
        CATALOG_TRY_VM_IP="$vm_ip" \
        CATALOG_TRY_EXIT_SIGNATURE="$ct_exit_signature" \
        CATALOG_TRY_PORT="$ct_port" \
        CATALOG_TRY_ENDPOINT="$ct_endpoint" \
        CATALOG_TRY_INIT_TIMEOUT="$ct_init_timeout" \
            bash "$deploy_script"
    ) ; then
        _r42_print_fail "element deploy failed (see playbook output above)"
        return 1
    fi
    _r42_print_check "element deployed on ${vm_ssh}:${remote_dir}"

    # 12. Final summary - mirror the intro layout (section + aligned key:value).
    #
    # NB on the smoke check line below : if we reached this point, the Ansible
    # smoke task returned 0 (the wrapper would have exited non-zero otherwise
    # and we'd never get here). So `✓ PASS` is implicit ; we just surface the
    # mode (L2 strict / L1 fallback) for the operator's situational awareness.
    # The L2/L1 detection mirrors the playbook's `when:` predicates exactly.
    local _smoke_label _smoke_color_open
    if [[ "$ct_mode" == "service" && -n "$ct_port" ]]; then
        _smoke_label="L2 service HTTP poll (port ${ct_port}${ct_endpoint})"
        _smoke_color_open='\033[1;32m'
    elif [[ "$ct_mode" == "oneshot" && -n "$ct_exit_signature" ]]; then
        _smoke_label="L2 oneshot signature grep"
        _smoke_color_open='\033[1;32m'
    else
        _smoke_label="L1 fallback (docker ps -a, any container)"
        _smoke_color_open='\033[1;33m'
    fi

    _r42_print_section "done - one usage VM ready"
    _r42_print_step "Element       : ${element_name}"
    _r42_print_step "Catalog path  : ${catalog_path}"
    _r42_print_step "Test VM       : ${vm_ssh}  (IP ${vm_ip})"
    _r42_print_step "Deployed at   : ${remote_dir}  (on the VM)"
    # Smoke check line : colored L?-label (green=L2, yellow=L1) + green ✓ PASS.
    # %s for the label defuses any format-meta in $ct_port / $ct_exit_signature.
    printf "    \033[34m➜\033[0m Smoke check   : ${_smoke_color_open}%s\033[0m  \033[1;32m✓ PASS\033[0m\n" "$_smoke_label"

    _r42_print_section "next steps"
    _r42_print_step "deploy again  : range42-context catalog-try ${catalog_path}"
    _r42_print_step "connect to VM : range42-context ssh ${vm_ssh}"
    _r42_print_step "                (alt : ssh ${vm_ssh})"
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
    printf "    ${N}snapshot-list${R}                  ${D}list snapshots of all scenario VMs${R}\n"
    printf "    ${N}revert${R} <name>                  ${D}revert all scenario VMs to a snapshot${R}\n"
    echo ""
    printf "  ${C}info${R}\n"
    printf "    ${N}inventory${R}                      ${D}show ansible inventory tree${R}\n"
    printf "    ${N}passwords${R}                      ${D}show generated credentials${R}\n"
    printf "    ${N}ssh${R} <pattern>                  ${D}quick ssh to a VM by name${R}\n"
    printf "    ${N}debug${R}                          ${D}toggle verbose output (show/hide skipped tasks)${R}\n"
    printf "    ${N}help${R}                           ${D}show this help${R}\n"
    echo ""
    printf "  ${C}catalog-try (one usage VM for single catalog element validation)${R}\n"
    printf "    ${N}catalog-try${R} <path>             ${D}deploy + smoke-check a catalog element (e.g. docker/_ctf/hello)${R}\n"
    printf "    ${N}catalog-try-list${R}               ${D}list catalog-try elements (L1/L2) excluding docker/admin/*${R}\n"
    printf "    ${N}catalog-try-list-admin${R}         ${D}list catalog-try elements (L1/L2) under docker/admin/* only${R}\n"
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
        snapshot-list)      _r42_snapshot_list ;;
        revert)             _r42_revert "$@" ;;
        ssh-reload)     _r42_ssh_reload ;;
        inventory|inv)  _r42_inventory ;;
        passwords|pw)   _r42_passwords ;;
        ssh)            _r42_ssh "$@" ;;
        cd)             _r42_cd "$@" ;;
        debug)          _r42_debug ;;
        catalog-try)         _r42_catalog_try "$@" ;;
        catalog-try-list)        _r42_catalog_try_list "" "docker/admin/" ;;
        catalog-try-list-admin)  _r42_catalog_try_list_admin ;;
        help|--help|-h) _r42_help ;;
        *)
            _r42_print_fail "unknown command: $cmd"
            _r42_help
            return 1
            ;;
    esac
}
