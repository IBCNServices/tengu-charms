# pylint: disable=unused-argument
from charms.reactive import when, when_not
from charmhelpers.core import hookenv


@when('hadoop.installed')
@when_not('namenode.related')
def blocked():
    hookenv.status_set('blocked', 'Waiting for relation to NameNode')


@when('hadoop.installed', 'namenode.related')
@when_not('namenode.spec.mismatch', 'namenode.ready')
def waiting(namenode):  # pylint: disable=unused-argument
    hookenv.status_set('waiting', 'Waiting for NameNode')


@when('datanode.started')
def ready():
    hookenv.status_set('active', 'Ready')
