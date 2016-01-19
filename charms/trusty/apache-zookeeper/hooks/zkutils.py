#!/usr/bin/env python
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

import os
from charmhelpers.core.hookenv import local_unit, unit_private_ip
from jujubigdata import utils


def getid(unitID):
    return unitID.split("/")[1]


def update_zoo_cfg(zkid=getid(local_unit()), ip=unit_private_ip(), remove=False):
    '''
    Configuration for a Zookeeper quorum requires listing all unique servers
    (server.X=<ip>:2888:3888) in the zoo.cfg. This function updates server.X
    entries and restarts the zookeeper service.
    '''
    zookeeper_cfg = "{}/zoo.cfg".format(os.environ.get('ZOOCFGDIR', '/etc/zookeeper/conf'))
    key = "server.{}".format(zkid)
    value = "={}:2888:3888".format(ip)
    if remove:
        removeKV(zookeeper_cfg, key)
        return
    addKV(zookeeper_cfg, key, value)

    # restart the zk server after alterting zoo.cfg
    zookeeper_bin = os.environ.get('ZOO_BIN_DIR', '/usr/lib/zookeeper/bin')
    utils.run_as('zookeeper', '{}/zkServer.sh'.format(zookeeper_bin), 'restart')


def addKV(filePath, key, value):
    found = False
    with open(filePath) as f:
        contents = f.readlines()
        for l in range(0, len(contents)):
            if contents[l].startswith(key):
                contents[l] = key+value+"\n"
                found = True
    if not found:
        contents.append(key+value+"\n")
    with open(filePath, 'wb') as f:
        f.writelines(contents)


def removeKV(filePath, key):
    found = False
    with open(filePath) as f:
        contents = f.readlines()
        for l in range(0, len(contents)):
            if contents[l].startswith(key):
                contents.pop(l)
                found = True
                break
    if found:
        with open(filePath, 'wb') as f:
            f.writelines(contents)
