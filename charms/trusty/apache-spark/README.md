## Overview

### Spark 1.4.x cluster for YARN & HDFS
Apache Spark™ is a fast and general purpose engine for large-scale data
processing. Key features:

 * **Speed**

 Run programs up to 100x faster than Hadoop MapReduce in memory, or 10x faster
 on disk. Spark has an advanced DAG execution engine that supports cyclic data
 flow and in-memory computing.

 * **Ease of Use**

 Write applications quickly in Java, Scala or Python. Spark offers over 80
 high-level operators that make it easy to build parallel apps, and you can use
 it interactively from the Scala and Python shells.

 * **General Purpose Engine**

 Combine SQL, streaming, and complex analytics. Spark powers a stack of
 high-level tools including Shark for SQL, MLlib for machine learning, GraphX,
 and Spark Streaming. You can combine these frameworks seamlessly in the same
 application.


## Usage
This charm leverages our pluggable Hadoop model with the `hadoop-plugin`
interface. This means that you will need to deploy a base Apache Hadoop cluster
to run Spark. The suggested deployment method is to use the
[apache-hadoop-spark](https://jujucharms.com/apache-hadoop-spark/)
bundle. This will deploy the Apache Hadoop platform with a single Apache Spark
unit that communicates with the cluster by relating to the
`apache-hadoop-plugin` subordinate charm:

    juju-quickstart apache-hadoop-spark

Alternatively, you may manually deploy the recommended environment as follows:

    juju deploy apache-hadoop-hdfs-master hdfs-master
    juju deploy apache-hadoop-yarn-master yarn-master
    juju deploy apache-hadoop-compute-slave compute-slave
    juju deploy apache-hadoop-plugin plugin
    juju deploy apache-spark spark

    juju add-relation yarn-master hdfs-master
    juju add-relation compute-slave yarn-master
    juju add-relation compute-slave hdfs-master
    juju add-relation plugin yarn-master
    juju add-relation plugin hdfs-master
    juju add-relation spark plugin

Once deployment is complete, you can manually load and run Spark batch or
streaming jobs in a variety of ways:

 * **Spark shell**

 Spark’s shell provides a simple way to learn the API, as well as a powerful
 tool to analyze data interactively. It is available in either Scala or Python
 and can be run from the Spark unit as follows:

       juju ssh spark/0
       spark-shell # for interaction using scala
       pyspark     # for interaction using python

 * **Command line**

 SSH to the Spark unit and manually run a spark-submit job, for example:

       juju ssh spark/0
       spark-submit --class org.apache.spark.examples.SparkPi \
        --master yarn-client /usr/lib/spark/lib/spark-examples*.jar 10

 * **Apache Zeppelin visual service**

 Deploy Apache Zeppelin and relate it to the Spark unit:

       juju deploy apache-zeppelin zeppelin
       juju add-relation spark zeppelin

 Once the relation has been made, access the web interface at
 http://{spark_unit_ip_address}:9090

 * **IPyNotebook for Spark**

 The IPython Notebook is an interactive computational environment, in which you
 can combine code execution, rich text, mathematics, plots and rich media.
 Deploy IPython Notebook for Spark and relate it to the Spark unit:

       juju deploy apache-spark-notebook notebook
       juju add-relation spark notebook

 Once the relation has been made, access the web interface at
 http://{spark_unit_ip_address}:8880


## Configuration

 ### driver_memory
 Amount of memory Spark will request for the Master. Specify gigabytes (e.g.
 1g) or megabytes (e.g. 1024m). If running in `local` or `standalone` mode, you
 may also specify a percentage of total system memory (e.g. 50%).

 ### executor_memory
 Amount of memory Spark will request for each executor. Specify gigabytes (e.g.
 1g) or megabytes (e.g. 1024m). If running in `local` or `standalone` mode, you
 may also specify a percentage of total system memory (e.g. 50%). Take care
 when specifying percentages in local modes, as this value is for *each*
 executor. Your Spark job will fail if, for example, you set this value > 50%
 and attempt to run 2 or more executors.

 ### spark_bench_enabled
 Install the SparkBench benchmarking suite. If `true` (the default), this charm
 will download spark bench from the URL specified by `spark_bench_ppc64le`
 or `spark_bench_x86_64`, depending on the unit's architecture.

 ### spark-execution-mode
 Spark has four modes of execution: local, standalone, yarn-client, and
 yarn-cluster. The default mode is `yarn-client` and can be changed by setting
 the `spark_execution_mode` config variable.

  * ** Local **

  In Local mode, Spark processes jobs locally without any cluster resources.
  There are 3 ways to specify 'local' mode:

   * `local`

     Run Spark locally with one worker thread (i.e. no parallelism at all).

   * `local[K]`

     Run Spark locally with K worker threads (ideally, set this to the number
     of cores on your machine).

   * `local[*]`

     Run Spark locally with as many worker threads as logical cores on your
     machine.

  * ** Standalone **

  In `standalone` mode, Spark launches a Master and Worker daemon on the Spark
  unit. This mode is useful for simulating a distributed cluster environment
  without actually setting up a cluster.

  * ** YARN-client **

  In `yarn-client mode`, the driver runs in the client process, and the
  application master is only used for requesting resources from YARN.

  * ** YARN-cluster **

  In `yarn-cluster mode`, the Spark driver runs inside an application master
  process which is managed by YARN on the cluster, and the client can go away
  after initiating the application.


 ## Testing the deployment

 ### Smoke test spark-submit
 SSH to the Spark unit and run the SparkPi test as follows:

     juju ssh spark/0
     ~/sparkpi.sh
     exit

 ### Verify Job History
 Verify the Job History server shows the previous spark-submit test by
 exposing the service (`juju expose spark`) and visiting
 http://{spark_unit_ip_address}:18080


 ## Benchmarking

 Run the [Spark Bench](https://github.com/SparkTC/spark-bench) benchmarking
 suite to gauge the performance of your environment. Each enabled test is a
 separate action and can be called as follows:

     $ juju action do spark/0 pagerank
     Action queued with id: 88de9367-45a8-4a4b-835b-7660f467a45e
     $ juju action fetch --wait 0 88de9367-45a8-4a4b-835b-7660f467a45e
     results:
       meta:
         composite:
           direction: asc
           units: secs
           value: "77.939000"
         raw: |
           PageRank,2015-12-10-23:41:57,77.939000,71.888079,.922363,0,PageRank-MLlibConfig,,,,,10,12,,200000,4.0,1.3,0.15
         start: 2015-12-10T23:41:34Z
         stop: 2015-12-10T23:43:16Z
       results:
         duration:
           direction: asc
           units: secs
           value: "77.939000"
         throughput:
           direction: desc
           units: x/sec
           value: ".922363"
     status: completed
     timing:
       completed: 2015-12-10 23:43:59 +0000 UTC
       enqueued: 2015-12-10 23:42:10 +0000 UTC
       started: 2015-12-10 23:42:15 +0000 UTC

 Valid action names at this time are:

  * logisticregression
  * matrixfactorization
  * pagerank
  * sql
  * streaming
  * svdplusplus
  * svm
  * trianglecount


 ## Contact Information

- <bigdata@lists.ubuntu.com>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
