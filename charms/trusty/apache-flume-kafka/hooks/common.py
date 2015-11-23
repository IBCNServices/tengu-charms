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

    flume_reqs = ['packages', 'groups', 'users', 'dirs']
    dist_config = jujubigdata.utils.DistConfig(filename='dist.yaml',
                                               required_keys=flume_reqs)
    flume = callbacks.Flume(dist_config)
    manager = charmframework.Manager([
        {
            'name': 'flume',
            'provides': [
            ],
            'requires': [
                flume.verify_resources,
                jujubigdata.relations.FlumeAgent(),
                callbacks.update_blocked_status,  # not really a requirement, but best way to fit into framework
            ],
            'callbacks': [
                callbacks.update_working_status,
                flume.install,
                charmframework.helpers.render_template(
                    source='flume.conf.j2',
                    target=flume.dist_config.path('flume_conf') / 'flume.conf',
                    context={'dist_config': dist_config}
                ),
                flume.restart,
                callbacks.update_active_status,
            ],
            'cleanup': [
                callbacks.clear_active_flag,
                flume.stop,
                flume.cleanup,
                callbacks.update_blocked_status,
            ],
        },
    ])
    manager.manage()


if __name__ == '__main__':
    manage()
