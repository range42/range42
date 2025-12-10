#!/bin/bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# CONTEXT
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

GENERATE_SSH_KEYS="${GENERATE_SSH_KEYS:-yes}"
GENERATE_PASSWORDS="${GENERATE_PASSWORDS:-yes}"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# INPUT CONFIG FILE - (local)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

DEPLOYER_CONFIGURATION_FILE_PATH="./config/config_remote-deployer-cli.yml"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### IMPORTED VARIABLES FROM CONFIG FILE
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
# reminder naming structure
#
# <SCOPE>__<ORIGIN>__<TYPE>__<ROLE>__<SIDE>
#
#
# INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL
# INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL
# INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL
#
# note for later :
# - INFRASTRUCTURE__AUTO_GENERATED__SECRETS_YAML_FILE_LOCAL
# - INFRASTRUCTURE__AUTO_GENERATED__SECRETS_VAULT_FILE_LOCAL
#

INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL="./config/${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"
INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/ssh_keys"
INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/passwords.env"

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

warn_custom_setup() {
	echo ""
	print_red ':: WARNING :: You are diverging from the official setup.'
	# print_red '              You should first try the default setup.'
	echo ""
}

require_binary() {
	command -v "$1" >/dev/null 2>&1 || {
		printf 'ERROR: required binary not found: %s\n' "$1"
		exit 1
	}
}

generate_ssh_key_if_missing() {

	local KEY_PATH="$1"
	local KEY_COMMENT="$2"
	local KEY_PASSWORD="$3"

	mkdir -p "$(dirname "$KEY_PATH")"
	chmod 700 "$(dirname "$KEY_PATH")"

	#### Check if key already exists

	if [ -f "$KEY_PATH" ]; then
		print_red ':: WARNING ::'
		printf ':: SSH key exists and will not be overwrited => %s\n' "$KEY_PATH"
		echo ""
		print_red "Press ENTER to continue, or Ctrl+C to abort and clean the directory manually."
		echo ""

		read -r
		return 0
	fi

	#### Generate key :: auto and interactive mode

	printf ':: generating SSH key: %s\n' "$KEY_PATH"

	if [ -z "$KEY_PASSWORD" ]; then

		#
		# MANUAL MODE — NO AUTO PASSPHRASE
		# use ssh-keygen as interactive - ask the user for a password
		#
		ssh-keygen \
			-t ed25519 \
			-f "$KEY_PATH" \
			-C "$KEY_COMMENT"

	else

		#
		# AUTOMATED MODE — PASSPHRASE PROVIDED
		#
		ssh-keygen \
			-t ed25519 \
			-f "$KEY_PATH" \
			-C "$KEY_COMMENT" \
			-N "$KEY_PASSWORD"
	fi

	####  change perm on keys

	chmod 600 "$KEY_PATH"
	chmod 644 "$KEY_PATH.pub"

	return 1
}

generate_password() {
	pwgen -cs 32 1
}

warmup_mkdir_ssh_config() {

	local T_DIR="$1"
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

	printf 'INFRASTRUCTURE_CODENAME                            : %s\n' "$INFRASTRUCTURE_CODENAME"
	printf 'INFRASTRUCTURE_SCENARIO                            : %s\n' "$INFRASTRUCTURE_SCENARIO"
	printf 'INFRASTRUCTURE_PROXMOX_ADDRESS                     : %s\n' "$INFRASTRUCTURE_PROXMOX_ADDRESS"
	printf 'SSH_CLIENT__DST_CONFIG_DIR                         : %s\n' "$SSH_CLIENT__DST_CONFIG_DIR"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__DEFAULT               : %s\n' "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"

	# printf 'SSH_CONFIG_RANGE42_DEPLOYER_FILE         : %s\n' "$SSH_CONFIG_RANGE42_KEYS_DEPLOYER_FILE"

	echo ''

	printf 'SSH_CLIENT__DST_CONFIG_RANGE42_DIR                 : %s\n' "$SSH_CLIENT__DST_CONFIG_RANGE42_DIR"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI  : %s\n' "$SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_DIR                   : %s\n' "$SSH_CLIENT__SSH_KEYS_RANGE42_DIR"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI    : %s\n' "$SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"

	echo ''

	printf 'DEPLOYER_CLI_CONFIG_USER                           : %s\n' "$DEPLOYER_CLI_CONFIG_USER"
	printf 'DEPLOYER_CLI_CONFIG_SSH_NAME                       : %s\n' "$DEPLOYER_CLI_CONFIG_SSH_NAME"
	printf 'DEPLOYER_CLI_CONFIG_IP                             : %s\n' "$DEPLOYER_CLI_CONFIG_IP"
	printf 'DEPLOYER_CLI_CONFIG_PORT                           : %s\n' "$DEPLOYER_CLI_CONFIG_PORT"

	echo ''

	# exit 1
}

prepare_environment_credentials() {

	echo ""
	print_red ':: Preparing environment credentials'
	echo ""

	###########################################################################
	# WORKSPACE
	###########################################################################

	mkdir -p "$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL"
	chmod 700 "$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL"

	###########################################################################
	# SSH KEYS
	###########################################################################

	SSH_KEY_PX_ROOT="$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.root"
	SSH_KEY_PX_JUMP="$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.jump_user"
	SSH_KEY_DEPLOYER_ADMIN_ALICE="$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-deployer-key_alice"
	SSH_KEY_STUDENT_USER_BOB="$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob"

	if [ "$GENERATE_SSH_KEYS" = "yes" ]; then

		echo ""
		print_red ':: Generating SSH keys'
		echo ""

		PX_ROOT_PASSPHRASE="$(generate_password)"
		PX_JUMP_PASSPHRASE="$(generate_password)"
		DEPLOYER_PASSPHRASE="$(generate_password)"
		STUDENT_PASSPHRASE="$(generate_password)"

		# generate_ssh_key_if_missing \
		# 	"$SSH_KEY_PX_ROOT" \
		# 	"proxmox root ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
		# 	"$PX_ROOT_PASSPHRASE"

		# generate_ssh_key_if_missing \
		# 	"$SSH_KEY_PX_JUMP" \
		# 	"proxmox jump ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
		# 	"$PX_JUMP_PASSPHRASE"

		# generate_ssh_key_if_missing \
		# 	"$SSH_KEY_DEPLOYER_ADMIN_ALICE" \
		# 	"r42 deployer (admin) - alice ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
		# 	"$DEPLOYER_PASSPHRASE"

		# generate_ssh_key_if_missing \
		# 	"$SSH_KEY_STUDENT_USER_BOB" \
		# 	"r42 student  (user)  - bob   ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
		# 	"$STUDENT_PASSPHRASE"

		# PROXMOX root key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "$SSH_KEY_PX_ROOT" "proxmox root ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			PX_ROOT_PASSPHRASE="(unchanged)" # generate_ssh_key_if_missing return 0
		else
			PX_ROOT_PASSPHRASE="$TEMP_PASS" # generate_ssh_key_if_missing return 1
		fi

		# PROXMOX jump key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "$SSH_KEY_PX_JUMP" "proxmox jump ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			PX_JUMP_PASSPHRASE="(unchanged)"
		else
			PX_JUMP_PASSPHRASE="$TEMP_PASS"
		fi

		# ALICE admin key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "$SSH_KEY_DEPLOYER_ADMIN_ALICE" "r42 deployer (admin) - alice ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			DEPLOYER_PASSPHRASE="(unchanged)"
		else
			DEPLOYER_PASSPHRASE="$TEMP_PASS"
		fi

		# BOB student key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "$SSH_KEY_STUDENT_USER_BOB" "r42 student (user) - bob ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			STUDENT_PASSPHRASE="(unchanged)"
		else
			STUDENT_PASSPHRASE="$TEMP_PASS"
		fi

	else
		warn_custom_setup
		print_red 'Skipping SSH key generation'
		echo
	fi

	###########################################################################
	# PASSWORD / PASSPHRASE GENERATION
	###########################################################################

	if [ "$GENERATE_PASSWORDS" = "yes" ]; then

		echo ""
		print_red ':: Generating SSH key passphrases and user passwords'
		echo ""

		# User passwords (runtime users, not SSH)
		ALICE_USER_PASSWORD="$(generate_password)"
		BOB_USER_PASSWORD="$(generate_password)"

		{
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo "#"
			print_red "# AUTO-GENERATED - DO NOT COMMIT :) "
			echo "#"
			echo "#  - infrastructure : ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"
			echo "#  - scenario       : ${INFRASTRUCTURE_SCENARIO}"
			echo "#  - config file    : ${DEPLOYER_CONFIGURATION_FILE_PATH}"
			echo "#"
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo ""
			echo "    ---- SSH KEY PASSPHRASES ----"
			echo ""
			printf '    PX_ROOT_SSH_PASSPHRASE=%s    - %s \n' "$PX_ROOT_PASSPHRASE" "$SSH_KEY_PX_ROOT"
			printf '    PX_JUMP_SSH_PASSPHRASE=%s    - %s \n' "$PX_JUMP_PASSPHRASE" "$SSH_KEY_PX_JUMP"
			printf '    DEPLOYER_SSH_PASSPHRASE=%s   - %s \n' "$DEPLOYER_PASSPHRASE" "$SSH_KEY_DEPLOYER_ADMIN_ALICE"
			printf '    STUDENT_SSH_PASSPHRASE=%s    - %s \n' "$STUDENT_PASSPHRASE" "$SSH_KEY_STUDENT_USER_BOB"
			echo ""
			echo "    ---- USER PASSWORDS ----"
			echo ""
			printf '    ALICE_USER_PASSWORD=%s\n' "$ALICE_USER_PASSWORD"
			printf '    BOB_USER_PASSWORD=%s\n' "$BOB_USER_PASSWORD"
			echo ""
			echo ""
			echo ""
		} >"$INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL"

		printf '    proxmox root SSH keys passphrase      : %s - %s \n' "$PX_ROOT_PASSPHRASE" "$SSH_KEY_PX_ROOT"
		printf '    proxmox jump SSH keys passphrase      : %s - %s \n' "$PX_JUMP_PASSPHRASE" "$SSH_KEY_PX_JUMP"
		printf '    deployer (alice) SSH keys passphrase  : %s - %s \n' "$DEPLOYER_PASSPHRASE" "$SSH_KEY_DEPLOYER_ADMIN_ALICE"
		printf '    student  (bob)   SSH keys passphrase  : %s - %s \n' "$STUDENT_PASSPHRASE" "$SSH_KEY_STUDENT_USER_BOB"
		echo ""
		printf '    alice (deployer/admin) pwd  : %s\n' "$ALICE_USER_PASSWORD"
		printf '    bob   (student/user) pwd    : %s\n' "$BOB_USER_PASSWORD"
		echo ""

		chmod 600 "$INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL"

	else

		warn_custom_setup
		print_red ':: Password / passphrase generation disabled (manual mode) ? '

		echo ""

		generate_ssh_key_if_missing \
			"$SSH_KEY_PX_ROOT" \
			"proxmox root ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"

		generate_ssh_key_if_missing \
			"$SSH_KEY_PX_JUMP" \
			"proxmox jump ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"

		generate_ssh_key_if_missing \
			"$SSH_KEY_DEPLOYER_ADMIN_ALICE" \
			"r42 deployer (admin) - alice ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"

		generate_ssh_key_if_missing \
			"$SSH_KEY_STUDENT_USER_BOB" \
			"r42 student  (user)  - bob   ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"

	fi

	###########################################################################
	# SUMMARY
	###########################################################################

	echo ""
	print_red ':: Preparation completed'
	echo ""
	printf '    Environment : %s-%s\n' "$INFRASTRUCTURE_CODENAME" "$INFRASTRUCTURE_SCENARIO"
	printf '    SSH keys    : %s\n' "$INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL"
	printf '    Passwords   : %s\n' "$INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL"
	echo ""
	echo ""
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

	require_binary ssh-keygen
	require_binary ssh-copy-id
	#
	require_binary yq

	if [ "$GENERATE_PASSWORDS" = "yes" ]; then
		require_binary pwgen

	else
		echo "ok"
		exit 1

	fi

	print_variables

	prepare_environment_credentials

	# warmup_ssh_client_configuration
	# create_remote_deployer_playbook
	## start_install
	;;
esac
