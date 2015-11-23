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
"""
Common implementation for all hooks.
"""

import jujuresources
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.core import charmframework


def bootstrap_resources():
    """
    Install required resources defined in resources.yaml
    """
    if unitdata.kv().get('charm.bootstrapped', False):
        return True
    hookenv.status_set('maintenance', 'Installing base resources')
    mirror_url = jujuresources.config_get('resources_mirror')
    if not jujuresources.fetch(mirror_url=mirror_url):
        missing = jujuresources.invalid()
        hookenv.status_set('blocked', 'Unable to fetch required resource%s: %s' % (
            's' if len(missing) > 1 else '',
            ', '.join(missing),
        ))
        return False
    jujuresources.install(['pathlib', 'jujubigdata'])
    unitdata.kv().set('charm.bootstrapped', True)
    return True


def manage():
    if not bootstrap_resources():
        # defer until resources are available, since charmhelpers, and thus
        # the framework, are required (will require manual intervention)
        return

    import jujubigdata
    import callbacks

    kafka_reqs = ['vendor', 'packages', 'groups', 'users', 'dirs', 'ports']
    dist_config = jujubigdata.utils.DistConfig(filename='dist.yaml',
                                               required_keys=kafka_reqs)
    kafka = callbacks.Kafka(dist_config)
    manager = charmframework.Manager([
        {
            'name': 'kafka',
            'provides': [
                jujubigdata.relations.Kafka(port=dist_config.port('kafka'))
            ],
            'requires': [
                kafka.verify_resources,
                jujubigdata.relations.Zookeeper(),
                callbacks.update_blocked_status,  # not really a requirement, but best way to fit into framework
            ],
            'callbacks': [
                callbacks.update_working_status,
                kafka.install,
                kafka.configure_kafka,
                kafka.restart,
                charmframework.helpers.open_ports(
                    dist_config.exposed_ports('kafka')),
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                charmframework.helpers.close_ports(
                    dist_config.exposed_ports('kafka')),
                kafka.stop,
                kafka.cleanup,
                callbacks.update_blocked_status,
            ],
        },
    ])
    manager.manage()


if __name__ == '__main__':
    manage()
