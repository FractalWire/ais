#!/bin/bash
# run the docker stack

docker stack deploy -c docker/stack.devel.yml ais
