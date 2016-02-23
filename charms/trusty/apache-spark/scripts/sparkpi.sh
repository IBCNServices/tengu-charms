#!/bin/bash
set -eu

echo "Running SparkPi in ${MASTER} mode"
spark-submit --master ${MASTER} --class org.apache.spark.examples.SparkPi /usr/lib/spark/lib/spark-examples-*.jar 10
echo ""
