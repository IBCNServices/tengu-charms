# pylint: disable=unused-argument
from charms.reactive import when, when_none, is_state
from charmhelpers.core.hookenv import status_set


@when('hadoop.installed')
@when_none('namenode.spec.mismatch', 'resourcemanager.spec.mismatch')
def update_status():
    hdfs_rel = is_state('namenode.related')
    yarn_rel = is_state('resourcemanager.related')
    hdfs_ready = is_state('namenode.ready')
    yarn_ready = is_state('resourcemanager.ready')

    if not (hdfs_rel or yarn_rel):
        status_set('blocked', 'Waiting for relation to ResourceManager and/or NameNode')
    elif hdfs_rel and not hdfs_ready:
        status_set('waiting', 'Waiting for NameNode')
    elif yarn_rel and not yarn_ready:
        status_set('waiting', 'Waiting for ResourceManager')
    else:
        ready = []
        if hdfs_ready:
            ready.append('DataNode')
        if yarn_ready:
            ready.append('NodeManager')
        status_set('active', 'Ready ({})'.format(' & '.join(ready)))
