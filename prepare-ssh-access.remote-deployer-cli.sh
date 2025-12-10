#!/bin/bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

DEPLOYER_CONFIGURATION_FILE_PATH="./config/config_remote-deployer-cli.yml"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

INFRASTRUCTURE_CODENAME=$(
	yq -r '.infrastructure_codename' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)

INFRASTRUCTURE_SCENARIO=$(
	yq -r '.infrastructure_scenario' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)

INFRASTRUCTURE_PROXMOX_ADDRESS=$(
	yq -r '.infrastructure_proxmox_address' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

SSH_CLIENT__DST_CONFIG_DIR=$(
	yq -r '.ssh_client__dst_config_dir' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)

SSH_CLIENT__DST_CONFIG_FILE__DEFAULT="$SSH_CLIENT__DST_CONFIG_DIR/config"
#
SSH_CLIENT__DST_CONFIG_RANGE42_DIR="$SSH_CLIENT__DST_CONFIG_DIR/range42-$INFRASTRUCTURE_CODENAME"
SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI="$SSH_CLIENT__DST_CONFIG_RANGE42_DIR/config_range42-$INFRASTRUCTURE_CODENAME"

SSH_CLIENT__SSH_KEYS_RANGE42_DIR="$SSH_CLIENT__DST_CONFIG_RANGE42_DIR/keys"
SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI="$SSH_CLIENT__SSH_KEYS_RANGE42_DIR/range42.$INFRASTRUCTURE_CODENAME.deployer-cli"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

DEPLOYER_CLI_CONFIG_SSH_NAME="range42.$INFRASTRUCTURE_CODENAME.deployer-cli"

DEPLOYER_CLI_CONFIG_IP=$(
	yq -r '.deployer_cli_ip' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)
DEPLOYER_CLI_CONFIG_USER=$(
	yq -r '.deployer_cli_user' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)
DEPLOYER_CLI_CONFIG_PORT=$(
	yq -r '.deployer_cli_ssh_port' "$DEPLOYER_CONFIGURATION_FILE_PATH"
)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####




#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

usage() {
	printf '\n\n'
	printf 'NAME\n'
	printf '  %s - Install deployer-cli console\n\n' "$SCRIPT_NAME"

	printf 'SYNOPSIS\n'
	printf '  %s [-h|--help]\n\n' "$SCRIPT_NAME"

	printf 'EXAMPLE\n'
	printf '  %s\n' "$SCRIPT_NAME"
	printf '\n\n'
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

print_red() {
	if [ -t 1 ]; then

		printf '\033[31m%s\033[0m\n' "$1"

	else # remove color in logs files.
		printf '%s\n' "$1"
	fi
}

warmup_mkdir_ssh_config() {

	T_DIR="$1"
	if [ ! -d "$T_DIR" ]; then

		printf ':: CREATING directory : %s' "$T_DIR"
		mkdir -p "$T_DIR"
		chmod 700 "$T_DIR"
	else
		chmod 700 "$T_DIR"
	fi
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

print_variables() {

	printf 'INFRASTRUCTURE_CODENAME                : %s\n' "$INFRASTRUCTURE_CODENAME"
	printf 'INFRASTRUCTURE_SCENARIO                : %s\n' "$INFRASTRUCTURE_SCENARIO"
	printf 'INFRASTRUCTURE_PROXMOX_ADDRESS                : %s\n' "$INFRASTRUCTURE_PROXMOX_ADDRESS"
	printf 'SSH_CLIENT__DST_CONFIG_DIR                         : %s\n' "$SSH_CLIENT__DST_CONFIG_DIR"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__DEFAULT               : %s\n' "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"

	# printf 'SSH_CONFIG_RANGE42_DEPLOYER_FILE         : %s\n' "$SSH_CONFIG_RANGE42_KEYS_DEPLOYER_FILE"
	echo ''
	printf 'SSH_CLIENT__DST_CONFIG_RANGE42_DIR                   : %s\n' "$SSH_CLIENT__DST_CONFIG_RANGE42_DIR"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI    : %s\n' "$SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_DIR                     : %s\n' "$SSH_CLIENT__SSH_KEYS_RANGE42_DIR"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI      : %s\n' "$SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"

	echo ''

	printf 'DEPLOYER_CLI_CONFIG_USER  : %s\n' "$DEPLOYER_CLI_CONFIG_USER"
	printf 'DEPLOYER_CLI_CONFIG_SSH_NAME  : %s\n' "$DEPLOYER_CLI_CONFIG_SSH_NAME"
	printf 'DEPLOYER_CLI_CONFIG_IP        : %s\n' "$DEPLOYER_CLI_CONFIG_IP"
	printf 'DEPLOYER_CLI_CONFIG_PORT      : %s\n' "$DEPLOYER_CLI_CONFIG_PORT"

	echo ''

	# exit 1
}

warmup_ssh_client_configuration() {

	warmup_mkdir_ssh_config "$SSH_CLIENT__DST_CONFIG_DIR"
	warmup_mkdir_ssh_config "$SSH_CLIENT__DST_CONFIG_RANGE42_DIR"
	warmup_mkdir_ssh_config "$SSH_CLIENT__SSH_KEYS_RANGE42_DIR"

	if [ ! -f "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT" ]; then
		printf ':: CREATING .ssh config file : %s' "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"
		touch "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"
	fi

	# chmod 600 "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"

	#
	# INCLUDE IF MISSING
	#

	if ! grep -q "Include $SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI" "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"; then
		{
			echo ""
			echo "#### ####  #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
			echo ""
			echo "Include $SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI"
			echo ""
			echo "#### ####  #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		} >>"$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"
	fi

	# mkdir -p "$SSH_CONFIG_RANGE42_KEYS_DIR/backend_keys/"

	{
		echo ""
		echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		echo ""
		echo ""
		echo "Host $DEPLOYER_CLI_CONFIG_SSH_NAME"
		echo "  Hostname $DEPLOYER_CLI_CONFIG_IP"
		echo "  User $DEPLOYER_CLI_CONFIG_USER"
		echo "  Port $DEPLOYER_CLI_CONFIG_PORT"
		echo "  IdentityFile $SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"
		echo ""
		echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		echo ""
	} >>"$SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI"

	ssh-keygen -f "$SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"
	ssh-copy-id -i "$SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI.pub" "$DEPLOYER_CLI_CONFIG_USER@$DEPLOYER_CLI_CONFIG_IP" #-p "$DEPLOYER_CLI_CONFIG_PORT"
	# ssh "$DEPLOYER_CLI_CONFIG_SSH_NAME" 'whoami'/

	# echo " do : ssh-add $SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"
	# echo " do : ssh $DEPLOYER_CLI_CONFIG_SSH_NAME 'whoami'"
}

create_remote_deployer_playbook() {

	REMOTE_DEPLOYER_CLI_INVENTORY_FILE="./inventories/$DEPLOYER_CLI_CONFIG_SSH_NAME.yml"

	REMOTE_DEPLOYER_CLI_SH_FILE="./deploy_remote_deployer-cli.sh"
	REMOTE_DEPLOYER_CLI_YML_FILE="./deploy_remote_deployer-cli.yml"

	####
	#### create - playbook yml file
	####
	{
		echo ""
		echo "- hosts: $DEPLOYER_CLI_CONFIG_SSH_NAME"
		echo "  become: true"
		echo "  roles:"
		echo "    - configure.deployer-cli "
		echo "  vars:"
		echo "    DEPLOYER_CLI_USER : \"$DEPLOYER_CLI_CONFIG_USER\""
		echo "    INFRASTRUCTURE_CODENAME : \"$INFRASTRUCTURE_CODENAME\""
		echo "    INFRASTRUCTURE_SCENARIO : \"$INFRASTRUCTURE_SCENARIO\""
		echo "    INFRASTRUCTURE_PROXMOX_ADDRESS : \"$INFRASTRUCTURE_PROXMOX_ADDRESS\""
		echo "    # bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb : \"NO\""
		echo ""

	} >>"$REMOTE_DEPLOYER_CLI_YML_FILE" # "./deploy_remote_deployer-cli.yml"

	####
	#### create - playbook runner scripts file
	####
	{
		echo "#!/bin/bash"
		echo ""
		echo "ansible-playbook \\"
		echo " -i $REMOTE_DEPLOYER_CLI_INVENTORY_FILE\\"
		echo " $REMOTE_DEPLOYER_CLI_YML_FILE \\"
		echo " -K"

	} >>"$REMOTE_DEPLOYER_CLI_SH_FILE" # "./deploy_remote_deployer-cli.sh"

	chmod +x "$REMOTE_DEPLOYER_CLI_SH_FILE"

	####
	#### create - inventory file
	####

	mkdir -p ./inventories
	{
		echo "all:"
		echo "  children:"
		echo "    init_scripts:"
		echo "      hosts:"
		echo "        $DEPLOYER_CLI_CONFIG_SSH_NAME:"
	} >>"$REMOTE_DEPLOYER_CLI_INVENTORY_FILE" # "/inventories/$DEPLOYER_CLI_CONFIG_SSH_NAME.yml"

	####
	#### create - show debuginventory file
	####

	{
		echo "#!/bin/bash"
		echo ""
		echo "ansible-inventory -i \"./$DEPLOYER_CLI_CONFIG_SSH_NAME.yml\" --graph"
		echo ""
	} >>"./inventories/show_inventory.$DEPLOYER_CLI_CONFIG_SSH_NAME.sh"

	chmod +x "./inventories/show_inventory.$DEPLOYER_CLI_CONFIG_SSH_NAME.sh"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

case "${1:-}" in
-h | --help)
	usage
	exit 0
	;;
-d | --debug)
	print_variables
	exit 0
	;;
*)

	print_variables
	warmup_ssh_client_configuration
	create_remote_deployer_playbook
	# start_install
	;;
esac
