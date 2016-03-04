#!/usr/bin/python3
from charms.reactive import when_not, set_state


@when_not('layered-charm.installed')
def install():
    print('install')
    set_state('layered-charm.installed')
