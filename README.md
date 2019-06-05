
This repository accompanies the articles:

* [Spark Streaming part 1: build data pipelines with Spark Structured Streaming](http://www.adaltas.com/en/2019/04/18/spark-streaming-data-pipelines-with-structured-streaming/)
* [Spark Streaming part 2: run Spark Structured Streaming pipelines in Hadoop](http://www.adaltas.com/en/2019/05/28/spark-structured-streaming-in-hadoop/)

## Setup a VM cluster and prepare the environment for the HDP installation

After cloning this repo, `cd` into it and run:

```bash
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa_ex
sudo tee -a /etc/hosts > /dev/null <<- EOF
  10.10.10.11 master01.cluster master01
  10.10.10.12 master02.cluster master02
  10.10.10.16 worker01.cluster worker01
  10.10.10.17 worker02.cluster worker02 
EOF
vagrant up
```
* Creates SSH keys on the host machine (`~/.ssh/id_rsa_ex`)
* Appends FQDNs of cluster nodes in `/etc/hosts` on the host machine (sudo needed)
* Sets up a cluster of 4 VMs running on a laptop with 32GB and 8 cores
  * The VMs FQDNs: `master01.cluster`, `master02.cluster`, `worker01.cluster`, `worker02.cluster`
  * The VMs have respectively 5/6/7/7 GB RAM, 1/1/3/2 cores, and all are running CentOS
  * Sets up SSH keys for root of each node (each VM)
  * Configures the `/etc/hosts` file on each node
  * [Prepares the environment for HDP](https://docs.hortonworks.com/HDPDocuments/Ambari-2.7.3.0/bk_ambari-installation/content/prepare_the_environment.html) on each node
  * Installs Python 3 concurrently to Python 2 on each node
* Only on the node `master01.cluster`:
  * Installs mysql and sets up a mysql database called `hive`, creates a `hive` user with `NewHivePass4!` password
  * Installs Ambari server and mysql jdbc connector
  * Starts `ambari-server`
* Notice that all nodes are provisioned via shell, which is a fragile procedural approach. Warnings may occur.

## Install HDP distribution with Ambari

Now the cluster should be ready for the Hadoop installation. You should be able to access Ambari's Web UI on http://master01.cluster:8080. Deploy a minimal Hadoop cluster with [HDP 3.1.0 installed through Apache Ambari 2.7.3](https://docs.hortonworks.com/HDPDocuments/Ambari-2.7.3.0/bk_ambari-installation/content/install-ambari-server.html). 

Guidelines for the Ambari Installer wizard:

* In "Target Hosts", enter the list of hosts with `master[01-02].cluster` and `worker[01-02].cluster` lines
* During the "Host Registration Information" provide the `~/.ssh/id_rsa_ex` SSH private key created earlier
* Install a minimal set of services:
  * ZooKeeper, YARN, HDFS, Hive, Tez on host `master01.cluster`
  * Kafka and Spark2 (including Spark2 History Server and Spark Thrift Server) on host `master02.cluster`
* Choose to connect to the existing mysql database with a URL `jdbc:mysql://master01.cluster/hive` (usr/pass `hive`/`NewHivePass4!`)
* Configure YARN containers: the memory allocated for containers at 6144MB, with a container memory threshold from the minimum value of 512MB to the maximum value of 6144MB
* Configure Spark2 to use Python 3 for PySpark - in "Spark2/Advanced spark2-env/content" field append `PYSPARK_PYTHON=python3`
* Spark's Driver program output tends to be rich in `INFO` level logs, which obfuscates the processing results outputted to console. In "Spark2/Advanced spark2-log4j-properties" `INFO` can be changed to `WARN` in "log4j.rootCategory" to make Spark output less verbose. When things don't work it's better to reverse to `INFO` log level
* Check that all services are running on hosts they were supposed to. Especially verify that Kafka Broker listens on `master02.cluster:6667` and Spark2 is available on `master02.cluster`

## New York state neighborhoods Shapefiles

[Zillow](https://www.zillow.com/) shared New York state neighborhoods Shapefile under the Creative Commons license. The files seem to disappeared from their website, but they are available in this repository in the directory "NYC_neighborhoods".

The Shapefiles include the outlines of New York City neighborhoods. They are used by the "NYC_neighborhoods/prep-nbhds.py" Python script that creates a "NYC_neighborhoods/nbhd.jsonl" file with neighborhoods data needed for the purpose of the part 1 and part 2 articles.

## Launching the code

The PySpark application *spark-streaming-X.py* (where X can be *console*, *hdfs*, or *memory*) can be submitted on a cluster from `master02.cluster` as `spark` user with a command:

```
spark-submit \
--master yarn --deploy-mode client \
--num-executors 2 --executor-cores 1 \
--executor-memory 5g --driver-memory 4g \
--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.3.0 \
--conf spark.sql.hive.thriftServer.singleSession=true \
/vagrant/spark-streaming-X.py
```

Once the application started, launch the stream of data from `master02.cluster` as `root` or `kafka`:

```bash
/vagrant/launch-streams.sh
```

The submitted application can get stuck while waiting for the resources if other application is already running on the cluster. Parameters for `spark-submit` are picked with assumption that only one such Spark application runs at the time. You may need to kill Spark Thrift Server, Tez application, or Spark application that you launched before.

The expected output of the application depends on which application has been submitted:

### spark-streaming-console.py

* The application reads data from Kafka topic, parses Kafka messages, processes it, and prints the results in console
* `TipsInConsole` query writes the streaming results to stdout of the Spark Driver
* It takes a while for the batches to be processed and printed. To speed it up, the application would need more resources
  * If you are interested only in development, you could submit the application without Hadoop, on Spark local (refer to part 1 of the series) 
  * Or submit the application on a real Hadoop cluster with more resources

### spark-streaming-hdfs.py

* The application reads data from Kafka topic, parses Kafka messages, and dumps unaltered raw data to HDFS
* Two streaming queries:
  * `PersistRawTaxiRides` query persists raw taxi rides data on HDFS path /user/spark/datalake/RidesRaw
  * `PersistRawTaxiFares` query persists raw taxi fares data on HDFS path /user/spark/datalake/FaresRaw

### spark-streaming-memory.py

* The application reads data from Kafka topic, parses Kafka messages, processes it, and mounts the results in memory
* Embedeed Spark Thrift Server is launched to expose streaming results stored in memory
* `TipsInMemory` query writes the streaming results in-memory of the Spark Driver
