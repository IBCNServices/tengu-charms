# pylint: disable=unused-argument
from charms.reactive import when, when_not
from charmhelpers.core import hookenv


if hookenv.metadata()['name'] == 'hadoop-client':
    # only report Ready status if deployed as standalone client, not as base layer
    @when('hadoop.installed')
    def report_ready(hadoop):
        hookenv.status_set('active', 'Ready')


@when_not('hadoop.related')
def report_blocked():
    hookenv.status_set('blocked', 'Waiting for relation to Hadoop Plugin')


@when('hadoop.related')
@when_not('hadoop.installed')
def report_waiting(hadoop):
    hookenv.status_set('waiting', 'Waiting for Plugin to become ready')
