#!/usr/bin/env bash

# execute as root or kafka user from master02.cluster host

su - kafka -c '( curl -s https://training.ververica.com/trainingData/nycTaxiRides.gz | \
  zcat | \
  split -l 10000 --filter="/usr/hdp/current/kafka-broker/bin/kafka-console-producer.sh \
  --broker-list master02.cluster:6667 --topic taxirides; sleep 0.2" \
  > /dev/null ) &'

su - kafka -c '( curl -s https://training.ververica.com/trainingData/nycTaxiFares.gz | \
  zcat | \
  split -l 10000 --filter="/usr/hdp/current/kafka-broker/bin/kafka-console-producer.sh \
  --broker-list master02.cluster:6667 --topic taxifares; sleep 0.2" \
  > /dev/null ) &'
