#!/usr/bin/env bash
set -e

if [[ "$1" == "ansible-playbook" ]]; then
  exec "$@"
fi

exec /bin/bash
