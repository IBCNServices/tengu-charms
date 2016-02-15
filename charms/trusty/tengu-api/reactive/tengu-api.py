#!/usr/bin/python
# source: https://www.howtoforge.com/nat_iptables
# pylint: disable=c0111,c0103,c0301

import subprocess
import os
import shutil
import pwd
import grp


from charmhelpers.core import templating, host
from charmhelpers.core.hookenv import open_port
from charms.reactive import set_state
from charms.reactive.decorators import when_file_changed
from charms.reactive import when, when_not, hook



@hook('upgrade-charm')
def upgrade():
    install()


@when_not('tengu-api.installed')
def install():
    install_tengu_api()
    set_state('tengu-api.installed')


@when('tengu-api.installed')
@when_not('tengu-api.started')
def start():
    host.service_start('tengu-api')
    set_state('tengu-api.started')


# Service will restart even if files change outside of Juju.
# `update-status` hook will run periodically checking the hash of those files.
@when_file_changed(
    '/etc/init/tengu-api.conf',
    '/opt/tengu-api/tengu_api.py')
@when('tengu-api.started')
def restart():
    host.service_restart('tengu-api')


def install_tengu_api():
    subprocess.check_call(['pip2', 'install', 'Jinja2', 'Flask', 'pyyaml', 'click'])
    mergecopytree('files/tengu-api', '/opt/tengu-api', symlinks=True)
    templating.render(
        source='upstart.conf',
        target='/etc/init/tengu-api.conf',
        context={}
    )
    open_port(5000)


def mergecopytree(src, dst, symlinks=False, ignore=None):
    """"Recursive copy src to dst, mergecopy directory if dst exists.
    OVERWRITES EXISTING FILES!!"""
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if symlinks and os.path.islink(src_item):
            if os.path.lexists(dst_item):
                os.remove(dst_item)
            os.symlink(os.readlink(src_item), dst_item)
        elif os.path.isdir(src_item):
            mergecopytree(src_item, dst_item, symlinks, ignore)
        else:
            shutil.copy2(src_item, dst_item)


def chownr(path, owner, group, follow_links=True):
    uid = pwd.getpwnam(owner).pw_uid
    gid = grp.getgrnam(group).gr_gid
    if follow_links:
        chown = os.chown
    else:
        chown = os.lchown
    chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            full = os.path.join(root, name)
            broken_symlink = os.path.lexists(full) and not os.path.exists(full)
            if not broken_symlink:
                chown(full, uid, gid)
