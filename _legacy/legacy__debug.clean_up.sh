#!/bin/bash

# set -euo pipefail
# debug file.

TARGET_USER="range42-operator"
TARGET_INFRASTRUCTURE_CODENAME="hv-hx"
PREPARE_SCRIPT_ROOT_LOCATION="/home/${TARGET_USER}/range42/range42"

echo ""
echo ":: Cleaning SSH directory"
echo ""

rm -rf "/home/${TARGET_USER}/.ssh/"

echo ""
echo "::  Cleaning config directories"
echo ""

rm -rf "${PREPARE_SCRIPT_ROOT_LOCATION}/config/${TARGET_INFRASTRUCTURE_CODENAME}-demo_lab"

rm "${PREPARE_SCRIPT_ROOT_LOCATION}/config/config_remote-deployer-cli.${TARGET_INFRASTRUCTURE_CODENAME}-demo_lab.yml"
rm "${PREPARE_SCRIPT_ROOT_LOCATION}/config/parent_config_remote-deployer-cli.${TARGET_INFRASTRUCTURE_CODENAME}.parent.yml"

rm "${PREPARE_SCRIPT_ROOT_LOCATION}/deploy.range42.${TARGET_INFRASTRUCTURE_CODENAME}.deployer-cli-demo_lab.sh"
rm "${PREPARE_SCRIPT_ROOT_LOCATION}/deploy.range42.${TARGET_INFRASTRUCTURE_CODENAME}.deployer-cli-demo_lab.yml"

echo ""
echo ":: Cleaning ssh-agent keys"
echo ""

if ssh-add -l >/dev/null 2>&1; then
	ssh-add -D
else
	echo ":: :: No ssh-agent running"
fi

echo ""
echo "done."
echo ""
