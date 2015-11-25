#!/bin/bash

echo "Running SparkPi in yarn-cluster mode"
spark-submit --class org.apache.spark.examples.SparkPi --master yarn-cluster /usr/lib/spark/lib/spark-examples*.jar 10
echo ""

echo "Running SparkPi in yarn-client mode"
spark-submit --class org.apache.spark.examples.SparkPi --master yarn-client /usr/lib/spark/lib/spark-examples*.jar 10
echo ""
