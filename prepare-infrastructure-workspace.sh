#!/bin/bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

SSH_KEY_PX_ROOT=""
SSH_KEY_PX_JUMP=""

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
	yq -r '.infrastructure_codename' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

INFRASTRUCTURE_SCENARIO=$(
	yq -r '.infrastructure_scenario' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

INFRASTRUCTURE_PROXMOX_ADDRESS=$(
	yq -r '.infrastructure_proxmox_address' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

SSH_CLIENT__DST_CONFIG_DIR=$(
	yq -r '.ssh_client__dst_config_dir' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

SSH_CLIENT__DST_CONFIG_FILE__DEFAULT="${SSH_CLIENT__DST_CONFIG_DIR}/config"
#
SSH_CLIENT__DST_CONFIG_RANGE42_DIR="${SSH_CLIENT__DST_CONFIG_DIR}/range42-${INFRASTRUCTURE_CODENAME}"
SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI="${SSH_CLIENT__DST_CONFIG_RANGE42_DIR}/config_range42-${INFRASTRUCTURE_CODENAME}"

SSH_CLIENT__SSH_KEYS_RANGE42_DIR="${SSH_CLIENT__DST_CONFIG_RANGE42_DIR}/keys"
SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI="${SSH_CLIENT__SSH_KEYS_RANGE42_DIR}/range42.${INFRASTRUCTURE_CODENAME}.deployer-cli"

STUDENT_ADDITIONNAL_KEYS_COUNT=$(
	yq -r '.student_additionnal_keys_count' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

DEPLOYER_CLI_CONFIG_SSH_NAME="range42.${INFRASTRUCTURE_CODENAME}.deployer-cli"

DEPLOYER_CLI_CONFIG_IP=$(
	yq -r '.deployer_cli_ip' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
DEPLOYER_CLI_CONFIG_USER=$(
	yq -r '.deployer_cli_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
DEPLOYER_CLI_CONFIG_PORT=$(
	yq -r '.deployer_cli_ssh_port' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
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
INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/vault"
INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/passwords.env"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#
# VAULT injected values - 4 PROXMOX API ACCESS
#

INFRASTRUCTURE_PROXMOX_API_HOST=$(
	yq -r '.proxmox_api_host' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_PROXMOX_NODE_NAME=$(
	yq -r '.proxmox_node' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_PROXMOX_API_USER=$(
	yq -r '.proxmox_api_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_PROXMOX_API_TOKEN_ID=$(
	yq -r '.proxmox_api_token_id' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET=$(
	yq -r '.proxmox_api_token_secret' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

## TODO - adapt the following.

DEBUG_PROXMOX_API_USER="${INFRASTRUCTURE_PROXMOX_API_USER}"
DEBUG_PROXMOX_API_TOKEN_ID="${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}"
DEBUG_PROXMOX_API_TOKEN_SECRET="${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#
# VAULT injected values - 5 - CLOUD-INIT USERS FOR DEPLOYER & TRAINEE VMs
#
# default_admin_vm_ci_user       - to_process
# default_admin_vm_ci_password   - to_process
#
# default_trainee_vm_ci_user     - to_process
# default_trainee_vm_ci_password - to_process
#
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#
# VAULT injected values - 6 - TAILSCALE, WAZUH, ETC.
#
INFRASTRUCTURE_TAILSCALE_AUTHKEY=$(
	yq -r '.vault_tailscale_authkey' "${DEPLOYER_CONFIGURATION_FILE_PATH}" # dev note :  must be rename to infrastructure_tailscale_authkey
)
INFRASTRUCTURE_TAILSCALE_APIKEY=$(
	yq -r '.vault_tailscale_apikey' "${DEPLOYER_CONFIGURATION_FILE_PATH}" # dev note :  must be rename to infrastructure_tailscale_apikey
)
INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD=$(
	yq -r '.WAZUH_PASSWORD' "${DEPLOYER_CONFIGURATION_FILE_PATH}" #  dev note :  must be rename to infrastructure_wazuh_admin_password
)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

usage() {
	printf '\n\n'
	printf 'NAME\n'
	printf '  %s - Install deployer-cli console\n\n' "${SCRIPT_NAME}"

	printf 'SYNOPSIS\n'
	printf '  %s [-h|--help]\n\n' "${SCRIPT_NAME}"

	printf 'EXAMPLE\n'
	printf '  %s\n' "${SCRIPT_NAME}"
	printf '\n\n'
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

print_color() {
	local COLOR_CODE="${1}"
	local MESSAGE="${2}"

	if [ -t 1 ]; then
		printf "\033[%sm%s\033[0m\n" "${COLOR_CODE}" "${MESSAGE}"
	else
		printf '%s\n' "${MESSAGE}"
	fi
}

print_red() { print_color "31" "${1}"; }
print_green() { print_color "32" "${1}"; }
print_blue() { print_color "34" "${1}"; }
print_cyan() { print_color "36" "${1}"; } # because i like cyan too :)

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

warn_custom_setup() {
	echo ""
	print_red ':: WARNING :: You are diverging from the official setup.'
	# print_red '              You should first try the default setup.'
	echo ""
}

require_binary() {
	command -v "${1}" >/dev/null 2>&1 || {
		printf 'ERROR: required binary not found: %s\n' "${1}"
		exit 1
	}
}

generate_ssh_key_if_missing() {

	local KEY_PATH="${1}"
	local KEY_COMMENT="${2}"
	local KEY_PASSWORD="${3}"

	mkdir -p "$(dirname "${KEY_PATH}")"
	chmod 700 "$(dirname "${KEY_PATH}")"

	#### Check if key already exists

	if [ -f "$KEY_PATH" ]; then
		print_red ' :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: ::'
		print_red ' ::::                            WARNING                                    ::'
		print_red ' :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: :::: ::'
		echo ""
		printf ' :: SSH key exists and will not be overwrited => %s\n' "$KEY_PATH"
		echo ""
		print_red "   Press ENTER to continue, or Ctrl+C to abort and clean the directory manually."
		echo ""
		echo ""
		echo ""

		read -r
		return 0
	fi

	#### Generate key :: auto and interactive mode

	printf ':: generating SSH key: %s\n' "${KEY_PATH}"

	if [ -z "$KEY_PASSWORD" ]; then

		#
		# MANUAL MODE — NO AUTO PASSPHRASE
		# use ssh-keygen as interactive - ask the user for a password
		#
		ssh-keygen \
			-t ed25519 \
			-f "${KEY_PATH}" \
			-C "${KEY_COMMENT}"

	else

		#
		# AUTOMATED MODE — PASSPHRASE PROVIDED
		#
		ssh-keygen \
			-t ed25519 \
			-f "${KEY_PATH}" \
			-C "${KEY_COMMENT}" \
			-N "${KEY_PASSWORD}"
	fi

	####  change perm on keys

	chmod 600 "${KEY_PATH}"
	chmod 644 "${KEY_PATH}.pub"

	return 1
}

generate_password() {
	pwgen -cs 32 1
}

warmup_mkdir_ssh_config() {

	local T_DIR="${1}"
	if [ ! -d "${T_DIR}" ]; then

		printf ':: CREATING directory : %s' "${T_DIR}"
		mkdir -p "${T_DIR}"
		chmod 700 "${T_DIR}"
	else
		chmod 700 "${T_DIR}"
	fi
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

print_variables() {

	printf 'INFRASTRUCTURE_CODENAME                            : %s\n' "${INFRASTRUCTURE_CODENAME}"
	printf 'INFRASTRUCTURE_SCENARIO                            : %s\n' "${INFRASTRUCTURE_SCENARIO}"
	printf 'INFRASTRUCTURE_PROXMOX_ADDRESS                     : %s\n' "${INFRASTRUCTURE_PROXMOX_ADDRESS}"
	printf 'SSH_CLIENT__DST_CONFIG_DIR                         : %s\n' "${SSH_CLIENT__DST_CONFIG_DIR}"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__DEFAULT               : %s\n' "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"

	# printf 'SSH_CONFIG_RANGE42_DEPLOYER_FILE         : %s\n' "$SSH_CONFIG_RANGE42_KEYS_DEPLOYER_FILE"

	echo ''

	printf 'SSH_CLIENT__DST_CONFIG_RANGE42_DIR                 : %s\n' "${SSH_CLIENT__DST_CONFIG_RANGE42_DIR}"
	printf 'SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI  : %s\n' "${SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI}"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_DIR                   : %s\n' "${SSH_CLIENT__SSH_KEYS_RANGE42_DIR}"
	printf 'SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI    : %s\n' "${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}"

	echo ''

	printf 'DEPLOYER_CLI_CONFIG_USER                           : %s\n' "${DEPLOYER_CLI_CONFIG_USER}"
	printf 'DEPLOYER_CLI_CONFIG_SSH_NAME                       : %s\n' "${DEPLOYER_CLI_CONFIG_SSH_NAME}"
	printf 'DEPLOYER_CLI_CONFIG_IP                             : %s\n' "${DEPLOYER_CLI_CONFIG_IP}"
	printf 'DEPLOYER_CLI_CONFIG_PORT                           : %s\n' "${DEPLOYER_CLI_CONFIG_PORT}"

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

	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys"
	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys"
	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal_students/"

	# I want avoid chmod -R ...
	#
	chmod 700 "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal_students/"

	###########################################################################
	# SSH KEYS
	###########################################################################

	SSH_KEY_PX_ROOT="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.root"
	SSH_KEY_PX_JUMP="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.jump_user"
	SSH_KEY_DEPLOYER_ADMIN_ALICE="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-deployer-key_alice"
	SSH_KEY_STUDENT_USER_BOB="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob"

	SSH_KEYS_STUDENT_ADDITIONNAL_DIR="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal.students/"
	# r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob"

	if [ "${GENERATE_SSH_KEYS}" = "yes" ]; then

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
		if generate_ssh_key_if_missing "${SSH_KEY_PX_ROOT}" "proxmox root ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "${TEMP_PASS}"; then
			PX_ROOT_PASSPHRASE="(unchanged)" # generate_ssh_key_if_missing return 0
		else
			PX_ROOT_PASSPHRASE="${TEMP_PASS}" # generate_ssh_key_if_missing return 1
		fi

		# PROXMOX jump key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_PX_JUMP}" "proxmox jump ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "${TEMP_PASS}"; then
			PX_JUMP_PASSPHRASE="(unchanged)"
		else
			PX_JUMP_PASSPHRASE="${TEMP_PASS}"
		fi

		# ALICE admin key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_DEPLOYER_ADMIN_ALICE}" "r42 deployer (admin) - alice ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			DEPLOYER_PASSPHRASE="(unchanged)"
		else
			DEPLOYER_PASSPHRASE="${TEMP_PASS}"
		fi

		# BOB student key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_STUDENT_USER_BOB}" "r42 student (user) - bob ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			STUDENT_PASSPHRASE="(unchanged)"
		else
			STUDENT_PASSPHRASE="${TEMP_PASS}"
		fi

		for i in $(seq 1 "${STUDENT_ADDITIONNAL_KEYS_COUNT}"); do

			STUDENT_KEY_PATH="${SSH_KEYS_STUDENT_ADDITIONNAL_DIR}/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob_${i}"

			TEMP_PASS="$(generate_password)"

			if generate_ssh_key_if_missing \
				"${STUDENT_KEY_PATH}" \
				"r42 student (user) - bob [extra ${i}] ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
				"${TEMP_PASS}"; then
				STUDENT_EXTRA_KEYS_PATHS+=("${STUDENT_KEY_PATH}")
				STUDENT_EXTRA_KEYS_PASSPHRASES+=("(unchanged)")
			else
				STUDENT_EXTRA_KEYS_PATHS+=("${STUDENT_KEY_PATH}")
				STUDENT_EXTRA_KEYS_PASSPHRASES+=("${TEMP_PASS}")
			fi

		done

		# for i in $(seq 1 "$STUDENT_ADDITIONNAL_KEYS_COUNT"); do

		# 	STUDENT_KEY_PATH="${SSH_KEYS_STUDENT_ADDITIONNAL_DIR}/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob_${i}"
		# 	TEMP_PASS="$(generate_password)"

		# 	if generate_ssh_key_if_missing \
		# 		"$STUDENT_KEY_PATH" \
		# 		"r42 student (user) - bob  - extra ${i}] ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" \
		# 		"$TEMP_PASS"; then
		# 		printf '  :: extra %s - passphrase : (unchanged)\n' "$i"
		# 	else
		# 		printf '  :: extra %s - passphrase : %s\n' "$i" "$TEMP_PASS"
		# 	fi

		# done

	else
		warn_custom_setup
		print_red 'Skipping SSH key generation'
		echo
	fi

	###########################################################################
	# PASSWORD / PASSPHRASE GENERATION
	###########################################################################

	if [ "${GENERATE_PASSWORDS}" = "yes" ]; then

		echo ""
		print_red ':: Generating SSH key passphrases and user passwords'
		echo ""

		# User passwords (runtime users, not SSH)
		ALICE_USER_PASSWORD="$(generate_password)"
		BOB_USER_PASSWORD="$(generate_password)"

		{
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo "#"
			printf "# AUTO-GENERATED - DO NOT COMMIT :) "
			echo "#"
			echo "#  - infrastructure : ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"
			echo "#  - scenario       : ${INFRASTRUCTURE_SCENARIO}"
			echo "#  - config file    : ${DEPLOYER_CONFIGURATION_FILE_PATH}"
			echo "#"
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo ""
			printf "    ---- SSH KEY PASSPHRASES ----"
			echo ""
			printf '    PX_ROOT_SSH_PASSPHRASE=%s    - %s \n' "${PX_ROOT_PASSPHRASE}" "${SSH_KEY_PX_ROOT}"
			printf '    PX_JUMP_SSH_PASSPHRASE=%s    - %s \n' "${PX_JUMP_PASSPHRASE}" "${SSH_KEY_PX_JUMP}"
			printf '    DEPLOYER_SSH_PASSPHRASE=%s   - %s \n' "${DEPLOYER_PASSPHRASE}" "${SSH_KEY_DEPLOYER_ADMIN_ALICE}"
			printf '    STUDENT_SSH_PASSPHRASE=%s    - %s \n' "${STUDENT_PASSPHRASE}" "${SSH_KEY_STUDENT_USER_BOB}"
			echo ""
			printf "    ---- USER PASSWORDS ----"
			echo ""
			printf '    ALICE_USER_PASSWORD=%s\n' "${ALICE_USER_PASSWORD}"
			printf '    BOB_USER_PASSWORD=%s\n' "${BOB_USER_PASSWORD}"
			echo ""
			echo ""
			echo ""
		} >"$INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL"

		printf '    proxmox root SSH keys passphrase      : %s - %s \n' "${PX_ROOT_PASSPHRASE}" "${SSH_KEY_PX_ROOT}"
		printf '    proxmox jump SSH keys passphrase      : %s - %s \n' "${PX_JUMP_PASSPHRASE}" "${SSH_KEY_PX_JUMP}"
		printf '    deployer (alice) SSH keys passphrase  : %s - %s \n' "${DEPLOYER_PASSPHRASE}" "${SSH_KEY_DEPLOYER_ADMIN_ALICE}"
		printf '    student  (bob)   SSH keys passphrase  : %s - %s \n' "${STUDENT_PASSPHRASE}" "${SSH_KEY_STUDENT_USER_BOB}"
		echo ""
		printf '    alice (deployer/admin) pwd  : %s\n' "${ALICE_USER_PASSWORD}"
		printf '    bob   (student/user) pwd    : %s\n' "${BOB_USER_PASSWORD}"
		echo ""

		#### extra keys :

		echo ""
		print_cyan "    ---- ADDITIONAL STUDENT SSH KEYS ----"
		echo ""

		for i in "${!STUDENT_EXTRA_KEYS_PATHS[@]}"; do
			printf '    STUDENT EXTRA bob_%02d SSH keys : %s - %s\n' \
				"$((i + 1))" \
				"${STUDENT_EXTRA_KEYS_PASSPHRASES[$i]}" \
				"${STUDENT_EXTRA_KEYS_PATHS[$i]}"
		done

		chmod 600 "${INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL}"

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
	print_cyan ':: Preparation completed'
	echo ""
	printf '    Environment : %s-%s\n' "${INFRASTRUCTURE_CODENAME}" "${INFRASTRUCTURE_SCENARIO}"
	printf '    SSH keys    : %s\n' "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}"
	printf '    Passwords   : %s\n' "${INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL}"
	echo ""
	echo ""
}

warmup_ssh_client_configuration() {

	warmup_mkdir_ssh_config "${SSH_CLIENT__DST_CONFIG_DIR}"
	warmup_mkdir_ssh_config "${SSH_CLIENT__DST_CONFIG_RANGE42_DIR}"
	warmup_mkdir_ssh_config "${SSH_CLIENT__SSH_KEYS_RANGE42_DIR}"

	if [ ! -f "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}" ]; then
		printf ':: CREATING .ssh config file : %s' "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"
		touch "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"
	fi

	# chmod 600 "$SSH_CLIENT__DST_CONFIG_FILE__DEFAULT"

	#
	# INCLUDE IF MISSING
	#

	if ! grep -q "Include $SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI" "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"; then
		{
			echo ""
			echo "#### ####  #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
			echo ""
			echo "Include ${SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI}"
			echo ""
			echo "#### ####  #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		} >>"${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"
	fi

	# mkdir -p "$SSH_CONFIG_RANGE42_KEYS_DIR/backend_keys/"

	{
		echo ""
		echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		echo ""
		echo ""
		echo "Host ${DEPLOYER_CLI_CONFIG_SSH_NAME}"
		echo "  Hostname ${DEPLOYER_CLI_CONFIG_IP}"
		echo "  User ${DEPLOYER_CLI_CONFIG_USER}"
		echo "  Port ${DEPLOYER_CLI_CONFIG_PORT}"
		echo "  IdentityFile ${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}"
		echo ""
		echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####"
		echo ""
	} >"${SSH_CLIENT__DST_CONFIG_FILE__RANGE42_DEPLOYER_CLI}"

	ssh-keygen -f "${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}"
	ssh-copy-id -i "${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}.pub" "${DEPLOYER_CLI_CONFIG_USER}@${DEPLOYER_CLI_CONFIG_IP}" #-p "$DEPLOYER_CLI_CONFIG_PORT"
	# ssh "$DEPLOYER_CLI_CONFIG_SSH_NAME" 'whoami'/

	# echo " do : ssh-add $SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI"
	# echo " do : ssh $DEPLOYER_CLI_CONFIG_SSH_NAME 'whoami'"
}

proxmox_load_root_ssh_key() {

	local SSH_KEY_PATH="${1}" # /path/to/px.hv-demo-ssh_cli.root
	local SSH_USER="${2}"     # root
	local PROXMOX_HOST="${3}" # 192.168.42.xxx

	local SSH_PUB="${SSH_KEY_PATH}.pub"

	printf "\n:: Managing SSH access for %s@%s\n" "${SSH_USER}" "${PROXMOX_HOST}"

	#
	# check if ssh-agent is running
	#

	if [ -z "${SSH_AUTH_SOCK}" ] || [ ! -S "${SSH_AUTH_SOCK}" ]; then
		print_red " - No ssh-agent running, starting a new one"
		eval "$(ssh-agent -s)" >/dev/null
	fi

	#
	# check if key already loaded in ssh-agent
	#

	if ssh-add -l | grep -q "$(ssh-keygen -lf "${SSH_KEY_PATH}" | awk '{print $2}')"; then
		printf " - SSH key already loaded in agent: %s\n" "${SSH_KEY_PATH}"
	else
		printf " - Loading SSH key into agent: %s\n" "${SSH_KEY_PATH}"
		ssh-add "${SSH_KEY_PATH}"
	fi

	#
	# check if pub key already existing on proxmox
	#

	printf " - Checking whether public key is already installed\n"

	if ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
		"${SSH_USER}@${PROXMOX_HOST}" true 2>/dev/null; then

		printf "   -> Public key already installed (authentication succeeded)\n"
		return 0
	fi

	#
	# if require, scp ssh key
	#

	printf " - Copying public key to Proxmox\n"
	ssh-copy-id -i "${SSH_PUB}" "${SSH_USER}@${PROXMOX_HOST}"

	if [ $? -eq 0 ]; then
		printf "   -> Public key successfully installed\n"
	else
		print_red "ERROR: Failed to install public key on Proxmox"
		exit 1
	fi
}

proxmox_fix_remote_locale() {

	local SSH_TARGET="${1}" # root@192.168.42.xxx
	local FIX_LOCALE

	FIX_LOCALE="C.UTF-8"
	printf " - Using locale: %s\n" "${FIX_LOCALE}"

	#
	# fixing /etc/default/locale on proxmox
	#

	ssh "$SSH_TARGET" "bash -c '
        echo \"LANG=${FIX_LOCALE}\" > /etc/default/locale
        echo \"LC_ALL=${FIX_LOCALE}\" >> /etc/default/locale
        echo \"LANGUAGE=${FIX_LOCALE}\" >> /etc/default/locale
    '"

	#
	# exec local-gen on proxmox
	#

	ssh "$SSH_TARGET" "locale-gen ${FIX_LOCALE} 2>/dev/null || true"

	#
	# export local in remote session (temp fix)
	#

	ssh "$SSH_TARGET" "export LANG=${FIX_LOCALE} LC_ALL=${FIX_LOCALE} LANGUAGE=${FIX_LOCALE}"

	printf " - Remote locale fixed successfully\n"
}

proxmox_generate_api_credentials() {

	local API_USER="${1//@pam/}" # API_master => we remove @pam if provided.
	local TOKEN_ID="${2}"        # API_master
	local SSH_TARGET="${3}"      # root@192.168.42.xxx

	printf '\n:: Generating Proxmox API credentials (idempotent)\n\n'

	#
	# check if provided proxmox user exists
	#

	if ssh "${SSH_TARGET}" "pveum user list | grep -q '^${API_USER}@pam'"; then
		printf " - User '${API_USER}@pam' already exists\n"
	else
		printf " - Creating user: ${API_USER}@pam\n"
		ssh "${SSH_TARGET}" "pveum user add ${API_USER}@pam"
	fi

	#
	# assign provided user administrator privileges
	#

	printf " - Assigning 'Administrator' role to ${API_USER}@pam\n"
	ssh "${SSH_TARGET}" \
		"pveum aclmod / -user ${API_USER}@pam -role Administrator"

	#
	# check if api token already exists
	#

	printf " - Checking if token '${TOKEN_ID}' already exists…\n"

	local TOKEN_INFO
	TOKEN_INFO=$(ssh "${SSH_TARGET}" \
		"pveum user token list ${API_USER}@pam | grep '^${API_USER}@pam!${TOKEN_ID}'" || true)

	if [ -n "$TOKEN_INFO" ]; then
		printf "   -> Token already exists, retrieving secret…\n"

		#
		# in case token exists :
		#   - try to fetch the existing token secret
		#     warning => Proxmox stores token secret only once !
		#

		local TOKEN_SECRET
		TOKEN_SECRET=$(ssh "${SSH_TARGET}" \
			"pveum user token list ${API_USER}@pam --output json" |
			jq -r ".[] | select(.token=='${TOKEN_ID}') | .value")

		if [ -z "${TOKEN_SECRET}" ] || [ "${TOKEN_SECRET}" = "null" ]; then
			echo ""
			echo ""
			print_red "   ERROR: Token exists but secret is not retrievable. (token was created manually ?)"
			print_red "   =====> You must delete the token or specify a new one with a different ID in the configuration."
			echo ""
			echo ""
			exit 1
		fi

		PROXMOX_API_TOKEN_ID="${TOKEN_ID}"
		PROXMOX_API_TOKEN_SECRET="${TOKEN_SECRET}"

		printf "   -> Token details : \n"
		printf "      Token ID      : %s\n" "${PROXMOX_API_TOKEN_ID}"
		printf "      Token SECRET  : %s\n" "${PROXMOX_API_TOKEN_SECRET}"

		return 0
	fi

	#
	# create new token (since it does not exist yet (best case :) )
	#

	printf " - Creating new token '${TOKEN_ID}' (JSON mode)\n"

	local TOKEN_JSON
	TOKEN_JSON=$(
		ssh "${SSH_TARGET}" \
			"pveum user token add ${API_USER}@pam ${TOKEN_ID} --privsep 0 --output-format json"
	)

	local TOKEN_SECRET
	TOKEN_SECRET=$(echo "${TOKEN_JSON}" | jq -r '.["value"]')

	if [ -z "${TOKEN_SECRET}" ] || [ "${TOKEN_SECRET}" = "null" ]; then
		print_red "ERROR: Failed to extract Proxmox API token secret (JSON parsing failed)"
		echo "${TOKEN_JSON}"
		exit 1
	fi

	#
	# output printing
	#

	PROXMOX_API_TOKEN_ID="${TOKEN_ID}"
	PROXMOX_API_TOKEN_SECRET="${TOKEN_SECRET}"

	printf "   -> Token created successfully\n"
	printf "      Token ID     : %s\n" "${PROXMOX_API_TOKEN_ID}"
	printf "      Token SECRET : %s\n" "${PROXMOX_API_TOKEN_SECRET}"

	DEBUG_PROXMOX_API_USER="${API_USER}@pam"
	DEBUG_PROXMOX_API_TOKEN_ID="${PROXMOX_API_TOKEN_ID}"
	DEBUG_PROXMOX_API_TOKEN_SECRET="${PROXMOX_API_TOKEN_SECRET}"

}

proxmox_api_call_test() {

	local PROXMOX_HOST_WITH_PORT="${1}" # 192.168.42.242
	# local API_USER="${2}"               # API_master
	local API_USER="${2//@pam/}" # API_master => we remove @pam if provided.
	local TOKEN_ID="${3}"        # API_master
	local TOKEN_SECRET="${4}"    # aaaaa....

	printf "\n:: Testing Proxmox API token on host %s\n\n" "${PROXMOX_HOST_WITH_PORT}"

	local RESPONSE
	RESPONSE=$(
		curl --silent --show-error --insecure \
			"https://${PROXMOX_HOST_WITH_PORT}/api2/json/nodes" \
			-H "Authorization: PVEAPIToken=${API_USER}@pam!${TOKEN_ID}=${TOKEN_SECRET}"
	)

	#
	# check for curl erorrs
	#

	if [ $? -ne 0 ]; then
		printf "\nERROR: Connection to Proxmox failed\n"
		return 1
	fi

	#
	# detect if promox returned an authentication failure
	#

	if echo "${RESPONSE}" | grep -q '"errors"'; then
		printf "\nERROR: Proxmox API returned an error:\n"
		echo "${RESPONSE}" | jq .
		return 1
	fi

	print_green ":: Proxmox API call successful! :: \n\n"
	echo "${RESPONSE}" | jq '.'
}

prepare_environment_ansible_vault() {

	print_red ":: Preparing Ansible vault"
	echo ""

	local VAULT_DIR="${INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL}"
	local VAULT_FILE="${VAULT_DIR}/default_vault.yml"
	local VAULT_PASS_FILE="${VAULT_DIR}/.vault_pass"

	mkdir -p "${VAULT_DIR}"
	chmod 700 "${VAULT_DIR}"

	#
	# pwgen a vault password
	#

	local VAULT_PASSWORD
	VAULT_PASSWORD="$(generate_password)"

	printf '%s\n' "${VAULT_PASSWORD}" >"${VAULT_PASS_FILE}"
	chmod 600 "${VAULT_PASS_FILE}"

	####

	local SSH_KEY_PX_ROOT_PUB_CONTENT
	local SSH_KEY_PX_JUMP_PUB_CONTENT
	local SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT
	local SSH_KEY_STUDENT_USER_PUB_CONTENT

	SSH_KEY_PX_ROOT_PUB_CONTENT="$(cat "${SSH_KEY_PX_ROOT}.pub")"
	SSH_KEY_PX_JUMP_PUB_CONTENT="$(cat "${SSH_KEY_PX_JUMP}.pub")"
	SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT="$(cat "${SSH_KEY_DEPLOYER_ADMIN_ALICE}.pub")"
	SSH_KEY_STUDENT_USER_PUB_CONTENT="$(cat "${SSH_KEY_STUDENT_USER_BOB}.pub")"

	# NOTE FOR LATER ::: NO DONT PUT THIS.
	# DEPLOYER_USER="$(yq -r '.deployer_user' "$DEPLOYER_CONFIGURATION_FILE_PATH")" # NO DONT PUT THIS.

	# CREATE VAULT FILE - (before encryption)
	cat >"${VAULT_FILE}" <<EOF


#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####  
#
#                      VAULT AUTO-GENERATED VAULT FILE 
#                           !!! DO NOT COMMIT !!! 
#
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####  
#
# Infrastructure: ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}
# scenario      : ${INFRASTRUCTURE_SCENARIO}
#
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####  



###############################################################################
# 1 - INFRASTRUCTURE INFORMATION
###############################################################################

infrastructure_codename: "${INFRASTRUCTURE_CODENAME}"
infrastructure_scenario: "${INFRASTRUCTURE_SCENARIO}"

proxmox_address: "${INFRASTRUCTURE_PROXMOX_ADDRESS}"
proxmox_node: "${INFRASTRUCTURE_PROXMOX_NODE_NAME}"

proxmox_api_host: "${INFRASTRUCTURE_PROXMOX_API_HOST}"
proxmox_api_user: "${INFRASTRUCTURE_PROXMOX_API_USER}"
proxmox_api_token_id: "${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}"
proxmox_api_token_secret: "${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"


###############################################################################
# 2 - SSH KEY PATHS 
###############################################################################
# ssh_key_px_root: "${SSH_KEY_PX_ROOT}"   # unused in vault
# ssh_key_px_jump: "${SSH_KEY_PX_JUMP}"   # unused in vault

ssh_key_deployer_admin: "${SSH_KEY_DEPLOYER_ADMIN_ALICE}"
ssh_key_student_user:   "${SSH_KEY_STUDENT_USER_BOB}"


###############################################################################
# 3 - SSH PUBLIC KEY CONTENT
###############################################################################
# ssh_key_px_root_pub_key: "${SSH_KEY_PX_ROOT_PUB_CONTENT}"  # unused in vault
# ssh_key_px_jump_pub_key: "${SSH_KEY_PX_JUMP_PUB_CONTENT}"  # unused in vault

ssh_key_deployer_admin_pub_key: "${SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT}"
ssh_key_student_user_pub_key:   "${SSH_KEY_STUDENT_USER_PUB_CONTENT}"


###############################################################################
# 4 - CLOUD-INIT USERS CONFIGURATION
###############################################################################
# --- Administrator VM (alice)
default_admin_vm_ci_user:        "alice"
default_admin_vm_ci_password:    "cmFuZ2UtNDIK"   # default password => echo range-42 | base64
default_admin_vm_ci_ssh_key:     "${SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT}"

# --- Student VM (bob)
default_trainee_vm_ci_user:      "bob"
default_trainee_vm_ci_password:  "cmFuZ2UtNDIK"   # default password => echo range-42 | base64
default_trainee_vm_ci_ssh_key:   "${SSH_KEY_STUDENT_USER_PUB_CONTENT}"


###############################################################################
# 5 - MISC 
###############################################################################

#
# DEV NOTE: 
#  - The follwing variables must be renamed to  deployer_cli_user_ssh_known_hosts
#

VAULT_operator_ssh_config_known_hosts: "${DEPLOYER_CLI_CONFIG_USER}"

vault_tailscale_apikey: "${INFRASTRUCTURE_TAILSCALE_APIKEY}"
vault_tailscale_authkey:"${INFRASTRUCTURE_TAILSCALE_AUTHKEY}"
WAZUH_PASSWORD:"${INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD}"


#
# VAULT_operator_ssh_config_known_hosts differ from backend_operator users (default_admin_vm_ci_user)
#



EOF

	# ENCRYP VAULT
	ansible-vault encrypt \
		"${VAULT_FILE}" \
		--vault-password-file "${VAULT_PASS_FILE}"

	echo ""
	echo ""
	print_red ":: VAULT created and encrypted"
	echo ""
	echo "  - Vault file      : ${VAULT_FILE}"
	echo "  - Vault password  : ${VAULT_PASS_FILE}"
	echo ""
}

create_remote_deployer_playbook() {

	REMOTE_DEPLOYER_CLI_INVENTORY_FILE="./inventories/${DEPLOYER_CLI_CONFIG_SSH_NAME}.yml"

	# REMOTE_DEPLOYER_CLI_SH_FILE="./deploy_remote_deployer-cli.sh"
	# REMOTE_DEPLOYER_CLI_YML_FILE="./deploy_remote_deployer-cli.yml"

	REMOTE_DEPLOYER_CLI_SH_FILE="./deploy.${DEPLOYER_CLI_CONFIG_SSH_NAME}-${INFRASTRUCTURE_SCENARIO}.sh"
	REMOTE_DEPLOYER_CLI_YML_FILE="./deploy.${DEPLOYER_CLI_CONFIG_SSH_NAME}-${INFRASTRUCTURE_SCENARIO}.yml"

	####
	#### create - playbook yml file
	####
	{
		echo ""
		echo "- hosts: ${DEPLOYER_CLI_CONFIG_SSH_NAME}"
		echo "  become: true"
		echo "  roles:"
		echo "    - configure.deployer-cli "
		echo "  vars:"
		echo "    DEPLOYER_CLI_USER : \"${DEPLOYER_CLI_CONFIG_USER}\""
		echo "    INFRASTRUCTURE_CODENAME : \"${INFRASTRUCTURE_CODENAME}\""
		echo "    INFRASTRUCTURE_SCENARIO : \"${INFRASTRUCTURE_SCENARIO}\""
		echo "    INFRASTRUCTURE_PROXMOX_ADDRESS : \"${INFRASTRUCTURE_PROXMOX_ADDRESS}\""
		echo "    INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL : \"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}\""

		echo "    # bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb : \"NO\""
		echo ""

	} >"${REMOTE_DEPLOYER_CLI_YML_FILE}" # "./deploy_remote_deployer-cli.yml"

	####
	#### create - playbook runner scripts file
	####
	{
		echo "#!/bin/bash"
		echo ""
		echo "ansible-playbook \\"
		echo " -i ${REMOTE_DEPLOYER_CLI_INVENTORY_FILE}\\"
		echo " ${REMOTE_DEPLOYER_CLI_YML_FILE} \\"
		echo " -K"

	} >"${REMOTE_DEPLOYER_CLI_SH_FILE}" # "./deploy_remote_deployer-cli.sh"

	chmod +x "${REMOTE_DEPLOYER_CLI_SH_FILE}"

	####
	#### create - inventory file
	####

	mkdir -p ./inventories
	{
		echo "all:"
		echo "  children:"
		echo "    init_scripts:"
		echo "      hosts:"
		echo "        ${DEPLOYER_CLI_CONFIG_SSH_NAME}:"
	} >"${REMOTE_DEPLOYER_CLI_INVENTORY_FILE}" # "/inventories/$DEPLOYER_CLI_CONFIG_SSH_NAME.yml"

	####
	#### create - show debuginventory file
	####

	{
		echo "#!/bin/bash"
		echo ""
		echo "ansible-inventory -i \"./${DEPLOYER_CLI_CONFIG_SSH_NAME}.yml\" --graph"
		echo ""
	} >"./inventories/show_inventory.${DEPLOYER_CLI_CONFIG_SSH_NAME}.sh"

	chmod +x "./inventories/show_inventory.${DEPLOYER_CLI_CONFIG_SSH_NAME}.sh"
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

	#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

	require_binary ssh-add
	require_binary ssh-keygen
	require_binary ssh-copy-id
	#
	require_binary yq

	if [ "${GENERATE_PASSWORDS}" = "yes" ]; then
		require_binary pwgen
	else
		exit 1
	fi

	#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

	print_variables

	prepare_environment_credentials

	prepare_environment_ansible_vault

	warmup_ssh_client_configuration

	proxmox_load_root_ssh_key \
		"${SSH_KEY_PX_ROOT}" \
		"root" \
		"${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_fix_remote_locale "root@${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_generate_api_credentials \
		"${DEBUG_PROXMOX_API_USER}" \
		"${DEBUG_PROXMOX_API_TOKEN_ID}" \
		"root@${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_api_call_test \
		"${INFRASTRUCTURE_PROXMOX_API_HOST}" \
		"${DEBUG_PROXMOX_API_USER}" \
		"${DEBUG_PROXMOX_API_TOKEN_ID}" \
		"${DEBUG_PROXMOX_API_TOKEN_SECRET}"

	# create_remote_deployer_playbook

	#
	#
	## start_install
	#
	#

	;;
esac
