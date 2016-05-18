#!/bin/bash
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This installs either OpenJDK or, if on Power hardware, IBM PPC Java.
# If successful, its only output should be two lines, the JAVA_HOME
# path, and the Java version, respectively.


set -e  # exit immediately if any step fails


java_version() {
    $JAVA_HOME/bin/java -version 2>&1 | head -n1 | awk -F\" '{print $2}'
}

find_java() {
    if [[ -z "$JAVA_HOME" ]]; then
        export JAVA_HOME=$(find $1 -name $2 | head -n1)
    fi
}


if [[ -n "$JAVA_HOME" ]]; then
    echo $JAVA_HOME
    java_version
    exit 0
fi



apt-get install -y software-properties-common &> /dev/null
add-apt-repository -y ppa:webupd8team/java &> /dev/null
apt-get update &> /dev/null
echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections &> /dev/null
apt-get install -y oracle-java7-installer &> /dev/null
export JAVA_HOME=/usr/lib/jvm/java-7-oracle
echo "JAVA_HOME=/usr/lib/jvm/java-7-oracle" >> /etc/environment



echo $JAVA_HOME
java_version
