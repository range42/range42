#!/bin/bash

ansible-playbook \
 -i ./inventories/range42.ds-px-pub-black-blackwood.deployer-cli.yml\
 ./deploy.range42.ds-px-pub-black-blackwood.deployer-cli-demo_lab.yml \
 -K
