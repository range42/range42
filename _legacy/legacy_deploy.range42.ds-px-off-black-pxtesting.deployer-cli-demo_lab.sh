#!/bin/bash

ansible-playbook \
 -i ./inventories/range42.ds-px-off-black-pxtesting.deployer-cli.yml\
 ./deploy.range42.ds-px-off-black-pxtesting.deployer-cli-demo_lab.yml \
 -K
