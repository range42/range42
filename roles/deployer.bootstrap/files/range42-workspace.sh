#!/usr/bin/env zsh
################################################################################
# range42-workspace — workspace export/import tool (zsh function)
#
# This file is SOURCED in .zshrc alongside range42-context.sh.
#
# Usage:
#   range42-workspace export                          — export active workspace as archive
#   range42-workspace export <codename> <scenario>    — export specific workspace
#   range42-workspace import <archive>                — import workspace from archive
#   range42-workspace help                            — show help
#
# Export produces:
#   ~/range42-workspace-export-CODENAME-SCENARIO-YYYYMMDD.r42.tar.gz
#
# Import:
#   - detects current user (whoami)
#   - rewrites /home/<old_user>/ → /home/<current_user>/ in config files
#   - clones git repos if absent
#   - recreates symlinks (secrets, scenario)
#   - installs SSH keys in ~/.ssh/range42/
#
################################################################################

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# constants (shared with range42-context)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

RANGE42_CONFIG_BASE_DIR="${RANGE42_CONFIG_BASE_DIR:-$HOME/range42.config}"
RANGE42_GIT_DIR="${RANGE42_GIT_DIR:-$HOME/range42}"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-workspace export (T48)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42ws_export() {

    local codename="$1"
    local scenario="$2"

    # if no args, use active workspace
    if [[ -z "$codename" ]]; then
        if [[ -z "$RANGE42_ACTIVE_WORKSPACE" ]]; then
            _r42_print_fail "no active workspace and no arguments provided"
            _r42_print_warning "usage: range42-workspace export <codename> <scenario>"
            return 1
        fi
        # parse CODENAME-SCENARIO from active workspace
        # the scenario is the last part after the last '-' that matches a known pattern
        # but since codenames contain dashes too, we use the config dir to find the split
        local target="$RANGE42_ACTIVE_WORKSPACE"
        local config_dir="$RANGE42_CONFIG_BASE_DIR/$target"
    else
        if [[ -z "$scenario" ]]; then
            _r42_print_fail "usage: range42-workspace export <codename> <scenario>"
            return 1
        fi
        local target="${codename}-${scenario}"
        local config_dir="$RANGE42_CONFIG_BASE_DIR/$target"
    fi

    # verify workspace exists
    if [[ ! -d "$config_dir" ]]; then
        _r42_print_fail "workspace not found: $config_dir"
        return 1
    fi

    _r42_print_section "exporting workspace: $target"

    local date_tag
    date_tag="$(date +%Y%m%d)"
    local archive_name="range42-workspace-export-${target}-${date_tag}.r42.tar.gz"
    local archive_path="$HOME/$archive_name"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    local export_dir="$tmp_dir/$target"

    # copy workspace content (resolve symlinks with -L)
    _r42_print_step "copying workspace (resolving symlinks)"
    cp -rL "$config_dir" "$export_dir"

    # generate metadata.yml
    _r42_print_step "generating metadata.yml"
    cat > "$export_dir/metadata.yml" <<EOF
# range42 workspace export metadata
# generated: $(date -Iseconds)
workspace: "$target"
exported_by: "$(whoami)"
exported_from: "$(hostname)"
original_home: "$HOME"
original_config_dir: "$config_dir"
original_git_dir: "$RANGE42_GIT_DIR"
EOF

    # copy ssh keys from ~/.ssh/range42/CODENAME-SCENARIO/ if they exist
    local ssh_keys_dir="$HOME/.ssh/range42/$target"
    if [[ -d "$ssh_keys_dir" ]]; then
        _r42_print_step "including SSH keys from $ssh_keys_dir"
        mkdir -p "$export_dir/dot_ssh_range42"
        cp -r "$ssh_keys_dir/"* "$export_dir/dot_ssh_range42/"
    fi

    # create archive
    _r42_print_step "creating archive: $archive_path"
    tar -czf "$archive_path" -C "$tmp_dir" "$target"

    # cleanup
    rm -rf "$tmp_dir"

    echo ""
    _r42_print_check "exported: $archive_path"
    _r42_print_step "size: $(du -h "$archive_path" | cut -f1)"
    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-workspace import (T49, T50, T51)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42ws_import() {

    local archive_path="$1"

    if [[ -z "$archive_path" || ! -f "$archive_path" ]]; then
        _r42_print_fail "usage: range42-workspace import <archive.r42.tar.gz>"
        return 1
    fi

    _r42_print_section "importing workspace from: $(basename "$archive_path")"

    local tmp_dir
    tmp_dir="$(mktemp -d)"

    # extract archive
    _r42_print_step "extracting archive"
    tar -xzf "$archive_path" -C "$tmp_dir"

    # find the workspace directory (should be the only dir in tmp)
    local workspace_dir
    workspace_dir="$(ls -1d "$tmp_dir"/*/ 2>/dev/null | head -1)"
    if [[ -z "$workspace_dir" ]]; then
        _r42_print_fail "invalid archive: no workspace directory found"
        rm -rf "$tmp_dir"
        return 1
    fi

    local target
    target="$(basename "$workspace_dir")"

    _r42_print_step "workspace: $target"

    # read metadata
    local old_home=""
    local old_user=""
    if [[ -f "$workspace_dir/metadata.yml" ]]; then
        old_home="$(grep 'original_home:' "$workspace_dir/metadata.yml" | sed 's/.*: *"//' | sed 's/"//')"
        old_user="$(grep 'exported_by:' "$workspace_dir/metadata.yml" | sed 's/.*: *"//' | sed 's/"//')"
        _r42_print_step "exported by: $old_user (home: $old_home)"
    fi

    local current_user
    current_user="$(whoami)"
    local current_home="$HOME"

    #### T49: rewrite paths if user differs

    if [[ -n "$old_home" && "$old_home" != "$current_home" ]]; then
        _r42_print_step "rewriting paths: $old_home → $current_home"
        find "$workspace_dir" -type f \( -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.env" -o -name "*.txt" \) \
            -exec sed -i "s|${old_home}|${current_home}|g" {} +
    fi

    #### deploy workspace to range42.config

    local dest_config_dir="$RANGE42_CONFIG_BASE_DIR/$target"

    if [[ -d "$dest_config_dir" ]]; then
        _r42_print_warning "workspace already exists: $dest_config_dir"
        _r42_print_warning "overwriting..."
    fi

    # remove metadata.yml and dot_ssh_range42 before copying to config dir
    rm -f "$workspace_dir/metadata.yml"
    local ssh_backup_dir="$workspace_dir/dot_ssh_range42"

    _r42_print_step "deploying to $dest_config_dir"
    mkdir -p "$dest_config_dir"
    # copy everything except dot_ssh_range42
    rsync -a --exclude='dot_ssh_range42' "$workspace_dir/" "$dest_config_dir/"

    #### T51: install SSH keys in ~/.ssh/range42/

    local ssh_dest_dir="$HOME/.ssh/range42/$target"
    if [[ -d "$ssh_backup_dir" ]]; then
        _r42_print_step "installing SSH keys to $ssh_dest_dir"
        mkdir -p "$ssh_dest_dir"
        cp -r "$ssh_backup_dir/"* "$ssh_dest_dir/"
        chmod 700 "$ssh_dest_dir"
        find "$ssh_dest_dir" -type f -exec chmod 600 {} +
        find "$ssh_dest_dir" -type f -name "*.pub" -exec chmod 644 {} +
    fi

    #### T49: clone git repos if absent

    _r42_print_step "checking git repos"

    local repos=(
        "range42-ansible_roles-proxmox_controller:https://github.com/range42/range42-ansible_roles-proxmox_controller.git"
        "range42-catalog:https://github.com/range42/range42-catalog.git"
        "range42-playbooks:https://github.com/range42/range42-playbooks.git"
        "range42-ansible_roles-debug-devkit:https://github.com/range42/range42-ansible_roles-debug-devkit.git"
        "range42-deployer-ui:https://github.com/range42/range42-deployer-ui.git"
        "range42-backend-api:https://github.com/range42/range42-backend-api.git"
    )

    mkdir -p "$RANGE42_GIT_DIR"
    local repo_entry repo_name repo_url
    for repo_entry in "${repos[@]}"; do
        repo_name="${repo_entry%%:*}"
        repo_url="${repo_entry#*:}"
        if [[ ! -d "$RANGE42_GIT_DIR/$repo_name" ]]; then
            _r42_print_step "cloning $repo_name"
            git clone "$repo_url" "$RANGE42_GIT_DIR/$repo_name" 2>/dev/null || {
                _r42_print_warning "failed to clone $repo_name — skipping"
            }
        else
            _r42_print_check "$repo_name already exists"
        fi
    done

    #### T50: recreate symlinks

    _r42_print_step "recreating symlinks"

    # parse scenario from target (last segment after last known codename pattern)
    # we look for the scenario directory in range42-playbooks
    local scenario_dir
    for d in "$RANGE42_GIT_DIR"/range42-playbooks/scenarios/*/; do
        local scenario_name="$(basename "$d")"
        if [[ "$target" == *"-${scenario_name}" ]]; then
            scenario_dir="$d"
            break
        fi
    done

    # secrets symlink in playbooks repo
    if [[ -n "$scenario_dir" ]]; then
        rm -f "${scenario_dir}/secrets" 2>/dev/null
        ln -sf "$dest_config_dir/secrets" "${scenario_dir}/secrets"
        _r42_print_check "symlink: ${scenario_dir}secrets → config secrets"

        # scenario symlink in config dir
        ln -sf "$scenario_dir" "$dest_config_dir/scenario"
        _r42_print_check "symlink: config/scenario → $scenario_dir"
    else
        _r42_print_warning "could not detect scenario directory in range42-playbooks"
    fi

    # secrets symlink in debug-devkit repo
    if [[ -d "$RANGE42_GIT_DIR/range42-ansible_roles-debug-devkit" ]]; then
        rm -f "$RANGE42_GIT_DIR/range42-ansible_roles-debug-devkit/secrets" 2>/dev/null
        ln -sf "$dest_config_dir/secrets" "$RANGE42_GIT_DIR/range42-ansible_roles-debug-devkit/secrets"
        _r42_print_check "symlink: debug-devkit/secrets → config secrets"
    fi

    #### cleanup

    rm -rf "$tmp_dir"

    echo ""
    _r42_print_check "import complete: $target"
    _r42_print_step "activate with: range42-context use <codename> <scenario>"
    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# range42-workspace help
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

_r42ws_help() {
    echo ""
    echo "usage: range42-workspace <command>"
    echo ""
    echo "commands:"
    echo "  export                              export active workspace as .r42.tar.gz"
    echo "  export <codename> <scenario>        export specific workspace"
    echo "  import <archive.r42.tar.gz>         import workspace from archive"
    echo "  help                                show this help"
    echo ""
    echo "export creates: ~/range42-workspace-export-CODENAME-SCENARIO-YYYYMMDD.r42.tar.gz"
    echo "import: rewrites paths, clones repos, recreates symlinks, installs SSH keys"
    echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# main entry point — range42-workspace function
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

range42-workspace() {

    local cmd="${1:-help}"
    shift 2>/dev/null

    case "$cmd" in
        export)         _r42ws_export "$@" ;;
        import)         _r42ws_import "$@" ;;
        help|--help|-h) _r42ws_help ;;
        *)
            _r42_print_fail "unknown command: $cmd"
            _r42ws_help
            return 1
            ;;
    esac
}
