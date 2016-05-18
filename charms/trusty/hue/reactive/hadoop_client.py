# pylint: disable=unused-argument
from charms.reactive import when, when_not
from charmhelpers.core import hookenv
from charms import layer


if hookenv.metadata()['name'] == 'hadoop-client':
    # only report Ready status if deployed as standalone client,
    # not if used as a base layer
    @when('hadoop.installed')
    def report_ready(hadoop):
        hookenv.status_set('active', 'Ready')


@when_not('hadoop.joined')
def report_blocked():
    cfg = layer.options('hadoop-client')
    if not cfg.get('silent'):
        hookenv.status_set('blocked', 'Waiting for relation to Hadoop Plugin')


@when('hadoop.joined')
@when_not('hadoop.installed')
def report_waiting(hadoop):
    cfg = layer.options('hadoop-client')
    if not cfg.get('silent'):
        hookenv.status_set('waiting', 'Waiting for Plugin to become ready')
