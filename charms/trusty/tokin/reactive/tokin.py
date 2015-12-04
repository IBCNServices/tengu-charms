#!/usr/bin/python
# pylint: disable=c0111,
import subprocess
import os
import shutil

from charmhelpers import fetch
from charmhelpers.core import templating, host

from charms.reactive import set_state
from charms.reactive import when, when_not
from charms.reactive import hookenv
from charms.reactive.decorators import when_file_changed

@when('tokin.ready')
@when_not('tokin.started')
def start():
    host.service_start('tokin')
    set_state('tokin.started')
    hookenv.status_set('Ready', 'Tokin ready')


# Flask reloads itself on file change, so restart is only needed if upstart
# file changed
@when_file_changed('/etc/init/tokin.conf')
@when('tokin.started')
def restart():
    host.service_restart('tokin')


@when('juju.upgraded')
def upgrade():
    install_tokin()


@when('juju.installed')
def install():
    install_tokin()


def install_tokin():
    hookenv.status_set('maintenance', 'Installing tokin')
    packages = ['python-pip']
    fetch.apt_install(fetch.filter_installed_packages(packages))
    subprocess.check_output([
        'pip', 'install', 'Jinja2', 'Flask', 'jujuclient', 'pyyaml'
    ])
    mergecopytree('files/tokin', '/opt/tokin',
                  symlinks=True)
    templating.render(
        source='upstart.conf',
        target='/etc/init/tokin.conf',
        context={}
    )


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
