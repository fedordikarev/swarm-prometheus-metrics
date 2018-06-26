#!/bin/sh

docker service create \
  --name swarm-prometheus-metrics \
  --mode global \
  --network metrics-network \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  --publish 8081:5000 \
  yatheo/containers_metrics:latest
