#!/usr/bin/python
import setup
setup.pre_install()
import sys
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir
import os


# Constants
REPOSITORY = os.path.realpath("/opt/wso2esb/current/repository")

# Hooks
hooks = hookenv.Hooks()

@hooks.hook('upgrade-charm')
def upgrade():
    """Upgrade hook"""
    print "upgrading charm"
    install()


@hooks.hook('install')
def install():
    """Install hook"""
    if not os.path.exists(REPOSITORY):
        os.makedirs(REPOSITORY)
    mergecopytree(charm_dir() + '/templates/repository', REPOSITORY)


# Hook logic
if __name__ == "__main__":
    hooks.execute(sys.argv)
