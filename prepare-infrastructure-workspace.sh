#!/bin/bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

SSH_KEY_PX_ROOT=""
SSH_KEY_PX_JUMP=""

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
# INPUT CONFIG FILE - (local)
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

DEPLOYER_CONFIGURATION_FILE_PATH="./config/config_remote-deployer-cli.TEMPLATE.yml"

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### IMPORTED VARIABLES FROM CONFIG FILE
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### ##### ##### CONTEXT - PASSWORG AUTO GENERATION

# GENERATE_SSH_KEYS="${GENERATE_SSH_KEYS:-yes}"
# GENERATE_PASSWORDS="${GENERATE_PASSWORDS:-yes}"

GENERATE_SSH_KEYS_PASSWORD=$(
	yq -r '.context_auto_generate_ssh_keys' "${DEPLOYER_CONFIGURATION_FILE_PATH}" |
		tr '[:lower:]' '[:upper:]'
)

GENERATE_VM_PASSWORD=$(
	yq -r '.context_auto_generate_vm_passwords' "${DEPLOYER_CONFIGURATION_FILE_PATH}" |
		tr '[:lower:]' '[:upper:]'
)

INFRASTRUCTURE_CODENAME=$(
	yq -r '.infrastructure_codename' "${DEPLOYER_CONFIGURATION_FILE_PATH}" |
		tr '[:upper:]' '[:lower:]'
)

INFRASTRUCTURE_SCENARIO=$(
	yq -r '.infrastructure_scenario' "${DEPLOYER_CONFIGURATION_FILE_PATH}" |
		tr '[:upper:]' '[:lower:]'
)

INFRASTRUCTURE_PROXMOX_ADDRESS=$(
	yq -r '.infrastructure_proxmox_address' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

#### #### ##### ##### CONTEXT - SSH KEYS

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

#### #### ##### ##### CONTEXT - DEPLOYER CLI

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

#### #### ##### ##### CONTEXT - FINAL FILES AND DIR LOCATIONS

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
INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/secrets"
INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL="${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}/passwords.env"

#### #### ##### ##### VAULT VALUES

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

#
# VAULT injected values - 5 - CLOUD-INIT USERS FOR DEPLOYER & TRAINEE VMs
#

INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER=$(
	yq -r '.default_admin_vm_ci_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD=$(
	yq -r '.default_admin_vm_ci_password' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER=$(
	yq -r '.default_trainee_vm_ci_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)
INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD=$(
	yq -r '.default_trainee_vm_ci_password' "${DEPLOYER_CONFIGURATION_FILE_PATH}"
)

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
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

#### #### ##### ##### LOCAL CONFIGURATION FILES OUTPUT FILES

DEPLOYER_CONFIGURATION_DST_FILE_PATH="./config/config_remote-deployer-cli.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}.yml"
# DEPLOYER_CONFIGURATION_PASSWORDS_DST_FILE_PATH="./config/config_remote-deployer-cli.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}.passwords"
DEPLOYER_CONFIGURATION_PARENT_FILE_PATH="./config/parent_config_remote-deployer-cli.${INFRASTRUCTURE_CODENAME}.parent.yml"

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
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

indent_cmd_output() {
	# when possible : indent/reformat/prefix external cmd output
	# do use this for cmd c

	local PREFIX="        " # 8 spaces

	while IFS= read -r line; do
		printf '         >  %s%s\n' "${PREFIX}" "${line}"
	done
}

print_color_format() {
	local COLOR_CODE="$1"
	shift
	local FORMAT="$1"
	shift

	if [ -t 1 ]; then
		printf "\033[%sm${FORMAT}\033[0m\n" "${COLOR_CODE}" "$@"
	else
		printf "${FORMAT}\n" "$@"
	fi
}

print_section() {
	local FORMAT="$1"
	shift
	printf "\n\033[34m----[ ${FORMAT} ]----\033[0m\n\n" "$@"
}

print_step() {
	local FORMAT="$1"
	shift
	printf "    \033[34m➜\033[0m ${FORMAT}\n" "$@"
}

print_check() {
	local FORMAT="$1"
	shift
	printf "    \033[32m✓\033[0m ${FORMAT}\n" "$@"
}

print_fail() {
	local FORMAT="$1"
	shift
	printf "    \033[31m✗\033[0m ${FORMAT}\n" "$@"
}

print_red_warning() {
	local FORMAT="$1"
	shift
	printf "    \033[31m▲\033[0m ${FORMAT}\n" "$@"

}

print_red() {
	local FORMAT="$1"
	shift
	printf "    \033[31m- ${FORMAT}\033[0m\n" "$@"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

warn_custom_setup() {
	echo ""
	print_red_warning '  :: WARNING :: You are diverging from the official setup.'
	# print_red '              You should first try the default setup.'
	echo ""
}

require_binary() {
	command -v "${1}" >/dev/null 2>&1 || {
		print_red_warning '  :: ERROR - Required binary not found: %s\n' "${1}"
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

		echo ""
		print_red_warning "WARNING : SSH key already exists : %s " "$KEY_PATH"
		print_red_warning "          Press ENTER to continue or Ctrl+C to abort and clean the directory manually."
		read -r
		return 0
	fi

	#### Generate key :: auto and interactive mode

	print_step 'Generating SSH key: %s' "${KEY_PATH}"

	if [ -z "$KEY_PASSWORD" ]; then

		#
		# MANUAL MODE — NO AUTO PASSPHRASE
		# use ssh-keygen as interactive - ask the user for a password
		#

		print_step "ssh-keygen :: interactive mode"

		ssh-keygen \
			-t ed25519 \
			-f "${KEY_PATH}" \
			-C "${KEY_COMMENT}" | indent_cmd_output

	else

		#
		# AUTOMATED MODE — PASSPHRASE PROVIDED
		#
		print_step "ssh-keygen :: automatic mode - provided passphrase "

		ssh-keygen \
			-t ed25519 \
			-f "${KEY_PATH}" \
			-C "${KEY_COMMENT}" \
			-N "${KEY_PASSWORD}" | indent_cmd_output
	fi

	#### change perm on keys

	print_step "Updating keys permissions"

	chmod 600 "${KEY_PATH}" | indent_cmd_output
	chmod 644 "${KEY_PATH}.pub" | indent_cmd_output

	return 1
}

generate_password() {
	pwgen -cs 32 1
}

warmup_mkdir_ssh_config() {

	local T_DIR="${1}"
	if [ ! -d "${T_DIR}" ]; then

		print_step 'Creating directory : %s' "${T_DIR}"
		mkdir -p "${T_DIR}"
		chmod 700 "${T_DIR}"
	else
		chmod 700 "${T_DIR}"
	fi
}

update_yaml_key() {
	local KEY="$1"
	local VALUE="$2"
	local T_FILE="$3"

	if [ ! -f "${T_FILE}" ]; then
		print_fail "YAML file not found: ${T_FILE}"
		return 1
	fi

	#### yaml quoted value
	local QUOTED_VALUE
	QUOTED_VALUE=$(printf '%s' "${VALUE}" | sed 's/"/\\"/g')

	#### Check if key exists
	if grep -qE "^${KEY}:" "${T_FILE}"; then
		print_step "Updating YAML key '%s'" "${KEY}"
		# Replace the existing key
		sed -i "s|^${KEY}:.*|${KEY}: \"${QUOTED_VALUE}\"|" "${T_FILE}"
	else
		print_step "Adding YAML key '%s' (not present)" "${KEY}"
		{
			echo ""
			echo "# Auto-added by installer"
			echo "${KEY}: \"${QUOTED_VALUE}\""
		} >>"${T_FILE}"
	fi

	print_check "YAML updated: %s" "${KEY}"
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

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

prepare_environment_passwords() {

	if [ "${GENERATE_VM_PASSWORD}" = "yes" ]; then

		INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD="$(generate_password)"
		INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD="$(generate_password)"
		INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD="$(generate_password)"

		# loaded in globals ...
		#
		# else
		# 	INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER=$(yq -r '.default_admin_vm_ci_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD=$(yq -r '.default_admin_vm_ci_password' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER=$(yq -r '.default_trainee_vm_ci_user' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD=$(yq -r '.default_trainee_vm_ci_password' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_TAILSCALE_AUTHKEY=$(yq -r '.vault_tailscale_authkey' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_TAILSCALE_APIKEY=$(yq -r '.vault_tailscale_apikey' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		# 	INFRASTRUCTURE_WAZUH_ADMIN_PASSWORD=$(yq -r '.WAZUH_PASSWORD' "${DEPLOYER_CONFIGURATION_FILE_PATH}")
		#
	fi

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

prepare_environment_ssh_keys() {

	print_section 'Preparing environment credentials'

	###########################################################################
	# WORKSPACE
	###########################################################################

	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys" | indent_cmd_output
	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys" | indent_cmd_output
	mkdir -p "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal_students/" | indent_cmd_output

	#### I want avoid chmod -R ...

	chmod 700 "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys" \
		"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal_students/" | indent_cmd_output

	###########################################################################
	# SSH KEYS
	###########################################################################

	SSH_KEY_PX_ROOT="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.root"
	SSH_KEY_PX_JUMP="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/jump_keys/px.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-ssh_cli.jump_user"
	SSH_KEY_DEPLOYER_ADMIN_ALICE="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/backend_keys/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-deployer-key_alice"
	SSH_KEY_STUDENT_USER_BOB="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob"

	SSH_KEYS_STUDENT_ADDITIONNAL_DIR="${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}/student_keys/additionnal.students/"
	# r42.${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}-student-key_bob"

	if [ "${GENERATE_SSH_KEYS_PASSWORD}" = "YES" ]; then

		echo ""
		print_step 'Generating SSH keys'
		echo ""

		PX_ROOT_PASSPHRASE="$(generate_password)"
		PX_JUMP_PASSPHRASE="$(generate_password)"
		DEPLOYER_PASSPHRASE="$(generate_password)"
		STUDENT_PASSPHRASE="$(generate_password)"

		#### PROXMOX root key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_PX_ROOT}" "proxmox root ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "${TEMP_PASS}"; then
			PX_ROOT_PASSPHRASE="(unchanged)" # generate_ssh_key_if_missing return 0
		else
			PX_ROOT_PASSPHRASE="${TEMP_PASS}" # generate_ssh_key_if_missing return 1
		fi

		#### PROXMOX jump key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_PX_JUMP}" "proxmox jump ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "${TEMP_PASS}"; then
			PX_JUMP_PASSPHRASE="(unchanged)"
		else
			PX_JUMP_PASSPHRASE="${TEMP_PASS}"
		fi

		#### ALICE admin key
		#
		TEMP_PASS="$(generate_password)"
		if generate_ssh_key_if_missing "${SSH_KEY_DEPLOYER_ADMIN_ALICE}" "r42 deployer (admin) - alice ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}" "$TEMP_PASS"; then
			DEPLOYER_PASSPHRASE="(unchanged)"
		else
			DEPLOYER_PASSPHRASE="${TEMP_PASS}"
		fi

		#### BOB student key
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

	else
		warn_custom_setup
		print_step 'Skipping SSH key generation'

	fi

	###########################################################################
	# PASSWORD / PASSPHRASE GENERATION
	###########################################################################

	if [ "${GENERATE_SSH_KEYS_PASSWORD}" = "YES" ]; then # yes, again this condition ; it's easier to manage like this.

		print_step ':: Generating SSH key passphrases and user passwords'
		echo ""

		#### User passwords - runtime users not SSH -
		ALICE_USER_PASSWORD="$(generate_password)"
		BOB_USER_PASSWORD="$(generate_password)"

		{
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo "#"
			echo "# AUTO-GENERATED - DO NOT COMMIT :) "
			echo "#"
			echo "#  - infrastructure : ${INFRASTRUCTURE_CODENAME}-${INFRASTRUCTURE_SCENARIO}"
			echo "#  - scenario       : ${INFRASTRUCTURE_SCENARIO}"
			echo "#  - config file    : ${DEPLOYER_CONFIGURATION_FILE_PATH}"
			echo "#"
			echo "#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### "
			echo ""
			echo "    ---- SSH KEY PASSPHRASES ----"
			echo ""
			printf '    PX_ROOT_SSH_PASSPHRASE=%s    - %s \n' "${PX_ROOT_PASSPHRASE}" "${SSH_KEY_PX_ROOT}"
			printf '    PX_JUMP_SSH_PASSPHRASE=%s    - %s \n' "${PX_JUMP_PASSPHRASE}" "${SSH_KEY_PX_JUMP}"
			printf '    DEPLOYER_SSH_PASSPHRASE=%s   - %s \n' "${DEPLOYER_PASSPHRASE}" "${SSH_KEY_DEPLOYER_ADMIN_ALICE}"
			printf '    STUDENT_SSH_PASSPHRASE=%s    - %s \n' "${STUDENT_PASSPHRASE}" "${SSH_KEY_STUDENT_USER_BOB}"
			echo ""
			echo "    ---- USER PASSWORDS ----"
			echo ""
			printf '    ALICE_USER_PASSWORD=%s\n' "${ALICE_USER_PASSWORD}"
			printf '    BOB_USER_PASSWORD=%s\n' "${BOB_USER_PASSWORD}"
			echo ""
			echo ""
			echo ""
		} >"$INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL"

		print_red '    proxmox root SSH keys passphrase      : %s - %s ' "${PX_ROOT_PASSPHRASE}" "${SSH_KEY_PX_ROOT}"
		print_red '    proxmox jump SSH keys passphrase      : %s - %s ' "${PX_JUMP_PASSPHRASE}" "${SSH_KEY_PX_JUMP}"
		print_red '    deployer (alice) SSH keys passphrase  : %s - %s ' "${DEPLOYER_PASSPHRASE}" "${SSH_KEY_DEPLOYER_ADMIN_ALICE}"
		print_red '    student  (bob)   SSH keys passphrase  : %s - %s ' "${STUDENT_PASSPHRASE}" "${SSH_KEY_STUDENT_USER_BOB}"
		echo ""
		print_red '    alice (deployer/admin) pwd  : %s' "${ALICE_USER_PASSWORD}"
		print_red '    bob   (student/user) pwd    : %s' "${BOB_USER_PASSWORD}"
		echo ""

		#### extra keys :

		echo ""
		print_red "    ---- ADDITIONAL STUDENT SSH KEYS ----"
		echo ""

		for i in "${!STUDENT_EXTRA_KEYS_PATHS[@]}"; do
			print_red '    STUDENT EXTRA bob_%02d SSH keys : %s - %s ' \
				"$((i + 1))" \
				"${STUDENT_EXTRA_KEYS_PASSPHRASES[$i]}" \
				"${STUDENT_EXTRA_KEYS_PATHS[$i]}"
		done

		chmod 600 "${INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL}" | indent_cmd_output

	else

		warn_custom_setup
		print_step 'Password / passphrase generation disabled (manual mode) ? '

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

	print_check 'Preparation completed'

	if [ "${GENERATE_SSH_KEYS_PASSWORD}" = "YES" ]; then

		echo ""
		print_red '    - Environment : %s-%s' "${INFRASTRUCTURE_CODENAME}" "${INFRASTRUCTURE_SCENARIO}"
		print_red '    - SSH keys    : %s' "${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}"
		print_red '    - Passwords   : %s' "${INFRASTRUCTURE__AUTO_GENERATED__PASSWORDS_FILE_LOCAL}"
		echo ""
	else
		echo ""
		print_red '    - Environment : %s-%s' "${INFRASTRUCTURE_CODENAME}" "${INFRASTRUCTURE_SCENARIO}"
		print_red '    - SSH keys    : manual_mode '
		print_red '    - Passwords   : manual_mode '

		warn_custom_setup

		for ssh_key_file in \
			"$SSH_KEY_PX_ROOT" \
			"$SSH_KEY_PX_JUMP" \
			"$SSH_KEY_DEPLOYER_ADMIN_ALICE" \
			"$SSH_KEY_STUDENT_USER_BOB"; do

			print_step "check ssh key access : ${ssh_key_file}"

			if [[ -z "$ssh_key_file" || ! -f "$ssh_key_file" ]]; then

				print_fail "error: missing or invalid key file: $ssh_key_file"
				exit 1
			fi

		done

	fi

	echo ""

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

warmup_ssh_client_configuration() {

	warmup_mkdir_ssh_config "${SSH_CLIENT__DST_CONFIG_DIR}"
	warmup_mkdir_ssh_config "${SSH_CLIENT__DST_CONFIG_RANGE42_DIR}"
	warmup_mkdir_ssh_config "${SSH_CLIENT__SSH_KEYS_RANGE42_DIR}"

	if [ ! -f "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}" ]; then
		print_step 'Creating .ssh config file : %s' "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"
		touch "${SSH_CLIENT__DST_CONFIG_FILE__DEFAULT}"
	fi

	#####
	#####  INCLUDE IF MISSING
	#####

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

	ssh-keygen -f "${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}" 2>&1
	ssh-copy-id -i "${SSH_CLIENT__SSH_KEYS_RANGE42_FILE__DEPLOYER_CLI}.pub" "${DEPLOYER_CLI_CONFIG_USER}@${DEPLOYER_CLI_CONFIG_IP}"

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

proxmox_load_root_ssh_key() {

	local SSH_KEY_PATH="${1}" # /path/to/px.hv-demo-ssh_cli.root
	local SSH_USER="${2}"     # root
	local PROXMOX_HOST="${3}" # 192.168.42.xxx

	local SSH_PUB="${SSH_KEY_PATH}.pub"

	print_step "Managing SSH keys for %s@%s" "${SSH_USER}" "${PROXMOX_HOST}"

	####
	#### check if ssh-agent is running
	####

	if [ -z "${SSH_AUTH_SOCK}" ] || [ ! -S "${SSH_AUTH_SOCK}" ]; then
		print_fail "No ssh-agent running, starting a new one"
		eval "$(ssh-agent -s)" >/dev/null
	fi

	####
	#### check if key already loaded in ssh-agent
	####

	if ssh-add -l | grep -q "$(ssh-keygen -lf "${SSH_KEY_PATH}" | awk '{print $2}')"; then
		print_check "SSH key already loaded in agent: %s" "${SSH_KEY_PATH}"
	else
		print_check "Loading SSH key into agent: %s" "${SSH_KEY_PATH}"
		ssh-add "${SSH_KEY_PATH}" | indent_cmd_output
	fi

	####
	#### check if pub key already existing on proxmox
	####

	echo ""
	print_step "Checking whether public key is already installed"

	if ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
		"${SSH_USER}@${PROXMOX_HOST}" true 2>/dev/null | indent_cmd_output; then

		print_check "Public key already installed (authentication succeeded)"
		return 0
	fi

	####  if require, scp ssh key

	print_step "Copying public key to Proxmox\n"
	ssh-copy-id -i "${SSH_PUB}" "${SSH_USER}@${PROXMOX_HOST}" | indent_cmd_output

	if [ $? -eq 0 ]; then
		print_check "Public key successfully installed"
	else
		print_fail "ERROR: Failed to install public key on Proxmox"
		exit 1
	fi
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

proxmox_fix_remote_locale() {

	local SSH_TARGET="${1}" # root@192.168.42.xxx
	local FIX_LOCALE

	print_section "Fixing locale on proxmox"

	FIX_LOCALE="C.UTF-8"
	print_check "Using locale: %s" "${FIX_LOCALE}"

	#
	# fixing /etc/default/locale on proxmox
	#

	ssh "$SSH_TARGET" "bash -c '
        echo \"LANG=${FIX_LOCALE}\" > /etc/default/locale
        echo \"LC_ALL=${FIX_LOCALE}\" >> /etc/default/locale
        echo \"LANGUAGE=${FIX_LOCALE}\" >> /etc/default/locale
    '" | indent_cmd_output # we can keep indent - we are now using ssh key.

	#
	# exec local-gen on proxmox
	#

	ssh "$SSH_TARGET" "locale-gen ${FIX_LOCALE} 2>/dev/null || true" | indent_cmd_output # we can keep indent - we are now using ssh key.

	#
	# export local in remote session (temp fix)
	#

	ssh "$SSH_TARGET" "export LANG=${FIX_LOCALE} LC_ALL=${FIX_LOCALE} LANGUAGE=${FIX_LOCALE}" | indent_cmd_output # we can keep indent - we are now using ssh key.

	print_check "Remote locale fixed successfully"
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

proxmox_generate_api_credentials() {

	local API_USER="${1//@pam/}"   # API_master => we remove @pam if provided.
	local API_USER_WITH_PAM="${1}" # API_master@pam
	local TOKEN_ID="${2}"          # API_master
	local SSH_TARGET="${3}"        # root@192.168.42.xxx

	print_section 'Create user '

	print_step "pveum user show ${API_USER}@pam "

	if ssh "${SSH_TARGET}" "pveum user show ${API_USER}@pam >/dev/null 2>&1"; then
		print_check "User %s@pam already exists" "${API_USER}"
	else
		print_step "Creating user: %s@pam" "${API_USER}"

		print_step "pveum user add ${API_USER}@pam"

		if ssh "${SSH_TARGET}" "pveum user add ${API_USER}@pam"; then
			print_check "User %s@pam successfully created" "${API_USER}"
		else
			print_fail "Failed to create Proxmox user %s@pam" "${API_USER}"
			# return 1
		fi
	fi

	print_section 'Generating Proxmox API credentials'

	####
	#### get FULL_TOKENID
	####

	FULL_TOKENID="${API_USER}@pam!${TOKEN_ID}"

	print_step "Checking if FULL_TOKENID '%s' exists on Proxmox." "${FULL_TOKENID}"

	TOKEN_EXISTS=false

	#
	# check existing tokens in JSON
	#
	print_step "pveum user token list ${API_USER}@pam --output-format json"

	TOKEN_JSON_LIST=$(ssh "${SSH_TARGET}" \
		"pveum user token list ${API_USER}@pam --output-format json" 2>/dev/null || true)

	# echo "json : pveum user token list ${API_USER}@pam --output-format json"

	if echo "${TOKEN_JSON_LIST}" | jq -e ".[] | select(.tokenid == \"${API_USER}\")" >/dev/null; then
		TOKEN_EXISTS=true
	else
		print_step "TokenId - not found - %s on Proxmox." "${API_USER}@pam"
	fi

	####
	#### check if token exists or import from configuration - ask with confirmation
	####

	if [ "${TOKEN_EXISTS}" = true ]; then
		print_check "Token '%s' already exists on Proxmox." "${FULL_TOKENID}"

		print_red_warning "A token with this ID already exists on the Proxmox server."
		print_red_warning "According to the configuration rules, the secret must come from:"
		print_red_warning "    ${DEPLOYER_CONFIGURATION_FILE_PATH}"
		echo ""

		# Check if we have a configured secret
		if [ -z "${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}" ] ||
			[ "${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}" = "null" ]; then

			print_fail "Token exists on Proxmox but no secret is defined in the configuration."
			print_red "Please edit your config file and provide the correct secret."
			exit 1
		fi

		print_step "Configuration file contains a token secret:"

		echo ""

		print_red_warning "WARNING : Do you want to continue using this secret? "
		print_red_warning "              - ${INFRASTRUCTURE_PROXMOX_API_HOST} "
		print_red_warning "              - ${FULL_TOKENID}"
		print_red_warning "              - ${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"

		print_red_warning "          Press ENTER to continue or Ctrl+C to abort."
		read -r

	else

		# update_yaml_key "proxmox_api_user" "${API_USER}@pam" "${DEPLOYER_CONFIGURATION_FILE_PATH}"
		# update_yaml_key "proxmox_api_token_id" "${TOKEN_ID}" "${DEPLOYER_CONFIGURATION_FILE_PATH}"
		# update_yaml_key "proxmox_api_token_secret""${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}" "${DEPLOYER_CONFIGURATION_FILE_PATH}"

		####
		#### Token does NOT exist then create new one
		####

		print_step "Creating new token '%s' on Proxmox" "${TOKEN_ID}"
		print_step "pveum user token add ${API_USER}@pam ${TOKEN_ID} --privsep 0 --output-format json"

		TOKEN_CREATE_JSON=$(
			ssh "${SSH_TARGET}" \
				"pveum user token add ${API_USER}@pam ${TOKEN_ID} --privsep 0 --output-format json" || true
		)

		echo "here"

		TOKEN_SECRET=$(echo "${TOKEN_CREATE_JSON}" | jq -r '.value')
		# fi

		####
		#### if proxmox failed to return secret - should not happen
		####

		if [ -z "${TOKEN_SECRET}" ] || [ "${TOKEN_SECRET}" = "null" ]; then
			# print_red "WARNING :: Could not extract token secret from Proxmox creation response."

			print_step "Falling back to secret from configuration file."

			if [[ -f "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}" && -r "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}" ]]; then
				print_check "Configuration file exists at location ${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"

				print_step "Importing proxmox settings from configuration file"

				INFRASTRUCTURE_PROXMOX_API_HOST=$(
					yq -r '.proxmox_api_host' "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"
				)
				INFRASTRUCTURE_PROXMOX_NODE_NAME=$(
					yq -r '.proxmox_node' "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"
				)
				INFRASTRUCTURE_PROXMOX_API_USER=$(
					yq -r '.proxmox_api_user' "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"
				)
				INFRASTRUCTURE_PROXMOX_API_TOKEN_ID=$(
					yq -r '.proxmox_api_token_id' "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"
				)
				INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET=$(
					yq -r '.proxmox_api_token_secret' "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}"
				)

			else
				print_fail "ERROR : parent configuration file  ${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH} not found" >&2
				exit 1
			fi

			echo ""

			print_red_warning "WARNING : Do you want to continue using this secret? "
			print_red_warning "              - ${INFRASTRUCTURE_PROXMOX_API_HOST} "
			print_red_warning "              - ${INFRASTRUCTURE_PROXMOX_API_USER}"
			print_red_warning "              - ${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"
			print_red_warning "          Press ENTER to continue or Ctrl+C to abort."

			read -r

		else
			INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET=${TOKEN_SECRET}
		fi

		# INFRASTRUCTURE_PROXMOX_API_TOKEN_ID="${TOKEN_ID}"
		# INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET="${TOKEN_SECRET}"

		# print_check "Token created successfully."
		# print_step "Token ID:     ${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}"
		# print_step "Token SECRET: ${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"

	fi

	print_check "Token imported from configuration. "
	print_step "API USER         : ${INFRASTRUCTURE_PROXMOX_API_USER}"
	print_step "API TOKEN_ID     : ${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}"
	print_step "API TOKEN_SECRET : ${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

proxmox_api_call_test() {

	local PROXMOX_HOST_WITH_PORT="${1}" # 192.168.42.242
	# local API_USER="${2}"               # API_master
	local API_USER="${2//@pam/}" # API_master => we remove @pam if provided.
	local TOKEN_ID="${3}"        # API_master
	local TOKEN_SECRET="${4}"    # aaaaa....

	print_step "Testing Proxmox API token on host %s" "${PROXMOX_HOST_WITH_PORT}"

	print_red " Using header - Authorization: PVEAPIToken=${API_USER}@pam!${TOKEN_ID}=${TOKEN_SECRET}"
	echo ""

	echo ">> curl --silent --show-error --insecure 'https://${PROXMOX_HOST_WITH_PORT}/api2/json/nodes' -H 'Authorization: PVEAPIToken=${API_USER}@pam!${TOKEN_ID}=${TOKEN_SECRET}'"
	echo

	BODY=$(curl --silent --show-error --insecure \
		"https://${PROXMOX_HOST_WITH_PORT}/api2/json/nodes" \
		-H "Authorization: PVEAPIToken=${API_USER}@pam!${TOKEN_ID}=${TOKEN_SECRET}" \
		-w "%{http_code}" \
		-o /tmp/proxmox_api_test_body.$$)

	HTTP_CODE="${BODY}"
	BODY="$(cat /tmp/proxmox_api_test_body.$$ | indent_cmd_output)"
	rm -f /tmp/proxmox_api_test_body.$$

	####
	#### Network or TLS failure
	####
	if [ "${HTTP_CODE}" = "000" ]; then
		print_fail "Connection to Proxmox failed (network/TLS error)"
	fi

	####
	#### Authentication failure → HTTP 401
	####
	if [ "${HTTP_CODE}" = "401" ]; then
		print_fail "Proxmox API authentication failed (invalid token)"
		print_red "HTTP 401 received"
	fi

	####
	#### Unexpected error codes
	####
	if ! echo "${HTTP_CODE}" | grep -qE "^(200)$"; then
		print_fail "Unexpected HTTP response from Proxmox: ${HTTP_CODE}"
		echo "${BODY}"
	fi

	print_check "Proxmox API token is valid"
	echo "${BODY}"

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

prepare_environment_ansible_vault() {

	print_section "Preparing Ansible vault"

	local VAULT_DIR="${INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL}"
	local VAULT_FILE="${VAULT_DIR}/default_vault.yml"
	local VAULT_PASS_FILE="${VAULT_DIR}/vault_pass.txt"

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

	print_step "Creating vault (clear version)"

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
default_admin_vm_ci_user:        "${INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_USER}"
default_admin_vm_ci_password:    "${INFRASTRUCTURE_DEFAULT_ADMIN_VM_CI_PASSWORD}" # default password => echo range-42 | base64
default_admin_vm_ci_ssh_key:     "${SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT}"

# --- Student VM (bob)
default_trainee_vm_ci_user:      "${INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_USER}" 
default_trainee_vm_ci_password:  "${INFRASTRUCTURE_DEFAULT_TRAINEE_VM_CI_PASSWORD}" # default password => echo range-42 | base64
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

	print_step "Encrypting vault"

	# ENCRYP VAULT
	ansible-vault encrypt \
		"${VAULT_FILE}" \
		--vault-password-file "${VAULT_PASS_FILE}" | indent_cmd_output

	print_check "Vault created and encrypted"

	print_red "    Vault file          : ${VAULT_FILE}"
	print_red "    Vault password      : $(cat "${VAULT_PASS_FILE}")"
	print_red "    Vault password file : ${VAULT_PASS_FILE}"

	echo ""
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

create_remote_deployer_playbook() {

	REMOTE_DEPLOYER_CLI_INVENTORY_FILE="./inventories/${DEPLOYER_CLI_CONFIG_SSH_NAME}.yml"

	# REMOTE_DEPLOYER_CLI_SH_FILE="./deploy_remote_deployer-cli.sh"
	# REMOTE_DEPLOYER_CLI_YML_FILE="./deploy_remote_deployer-cli.yml"

	REMOTE_DEPLOYER_CLI_SH_FILE="./deploy.${DEPLOYER_CLI_CONFIG_SSH_NAME}-${INFRASTRUCTURE_SCENARIO}.sh"
	REMOTE_DEPLOYER_CLI_YML_FILE="./deploy.${DEPLOYER_CLI_CONFIG_SSH_NAME}-${INFRASTRUCTURE_SCENARIO}.yml"

	####
	#### create - playbook yml file
	####

	print_section "creating playbook yml file"

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
		echo "    INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL :  \"${INFRASTRUCTURE__AUTO_GENERATED__CONFIG_DIR_LOCAL}\""
		echo "    INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL : \"${INFRASTRUCTURE__AUTO_GENERATED__SSH_KEYS_DIR_LOCAL}\""
		echo "    INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL : \"${INFRASTRUCTURE__AUTO_GENERATED__ANSIBLE_VAULT_DIR_LOCAL}\""

		echo "    # bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb : \"NO\""
		echo ""

	} >"${REMOTE_DEPLOYER_CLI_YML_FILE}" # "./deploy_remote_deployer-cli.yml"

	####
	#### create - playbook runner scripts file
	####

	print_step "Creating playbook sh file"

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

	print_step "Creating inventory file"

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

	print_step "Creating inventories - show script"

	{
		echo "#!/bin/bash"
		echo ""
		echo "ansible-inventory -i \"./${DEPLOYER_CLI_CONFIG_SSH_NAME}.yml\" --graph"
		echo ""
	} >"./inventories/show_inventory.${DEPLOYER_CLI_CONFIG_SSH_NAME}.sh"

	chmod +x "./inventories/show_inventory.${DEPLOYER_CLI_CONFIG_SSH_NAME}.sh"
}

backup_configuration_file() {

	local FILE_SRC="$1"
	local FILE_DST="$2"

	print_section "Configuration local backup"

	cp -f "${FILE_SRC}" "${FILE_DST}"

	print_step "Updating configuration ${FILE_DST}"

	update_yaml_key "proxmox_api_token_secret" "${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}" "${FILE_DST}"

	# local SSH_KEY_PX_ROOT_PUB_CONTENT
	# local SSH_KEY_PX_JUMP_PUB_CONTENT
	local SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT
	local SSH_KEY_STUDENT_USER_PUB_CONTENT

	# SSH_KEY_PX_ROOT_PUB_CONTENT="$(cat "${SSH_KEY_PX_ROOT}.pub")"
	# SSH_KEY_PX_JUMP_PUB_CONTENT="$(cat "${SSH_KEY_PX_JUMP}.pub")"
	SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT="$(cat "${SSH_KEY_DEPLOYER_ADMIN_ALICE}.pub")"
	SSH_KEY_STUDENT_USER_PUB_CONTENT="$(cat "${SSH_KEY_STUDENT_USER_BOB}.pub")"

	#
	update_yaml_key "default_admin_vm_ci_ssh_key" "${SSH_KEY_DEPLOYER_ADMIN_PUB_CONTENT}" "${FILE_DST}"
	update_yaml_key "default_trainee_vm_ci_ssh_key" "${SSH_KEY_STUDENT_USER_PUB_CONTENT}" "${FILE_DST}"

	print_check "YAML updated successfully."

}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
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

	if [[ "${GENERATE_SSH_KEYS_PASSWORD}" == "YES" || "${GENERATE_VM_PASSWORD}" == "YES" ]]; then
		require_binary pwgen
	else
		exit 1
	fi

	#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####

	print_variables

	prepare_environment_passwords
	prepare_environment_ssh_keys

	warmup_ssh_client_configuration

	proxmox_load_root_ssh_key \
		"${SSH_KEY_PX_ROOT}" \
		"root" \
		"${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_fix_remote_locale "root@${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_generate_api_credentials \
		"${INFRASTRUCTURE_PROXMOX_API_USER}" \
		"${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}" \
		"root@${INFRASTRUCTURE_PROXMOX_ADDRESS}"

	proxmox_api_call_test \
		"${INFRASTRUCTURE_PROXMOX_API_HOST}" \
		"${INFRASTRUCTURE_PROXMOX_API_USER}" \
		"${INFRASTRUCTURE_PROXMOX_API_TOKEN_ID}" \
		"${INFRASTRUCTURE_PROXMOX_API_TOKEN_SECRET}"

	prepare_environment_ansible_vault

	create_remote_deployer_playbook

	backup_configuration_file "${DEPLOYER_CONFIGURATION_FILE_PATH}" "${DEPLOYER_CONFIGURATION_DST_FILE_PATH}"
	backup_configuration_file "${DEPLOYER_CONFIGURATION_FILE_PATH}" "${DEPLOYER_CONFIGURATION_PARENT_FILE_PATH}" # parent will be use for child config to import proxmox settings.

	#
	#
	## start_install
	#
	#

	print_section "Preparation details"

	printf 'INFRASTRUCTURE_CODENAME                            : %s\n' "${INFRASTRUCTURE_CODENAME}"
	printf 'INFRASTRUCTURE_SCENARIO                            : %s\n' "${INFRASTRUCTURE_SCENARIO}"
	printf 'INFRASTRUCTURE_PROXMOX_ADDRESS                     : %s\n' "${INFRASTRUCTURE_PROXMOX_ADDRESS}"
	printf 'SSH_CLIENT__DST_CONFIG_DIR                         : %s\n' "${SSH_CLIENT__DST_CONFIG_DIR}"

	echo ""
	echo ""
	echo ""

	print_check "Preparation completed - ready to deploy "

	echo ""
	echo ""
	echo ""
	;;
esac
