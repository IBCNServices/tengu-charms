#!/usr/bin/env python
# pylint: disable=c0111,c0103,c0301
import subprocess
import os
import shutil
import base64

from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import charm_dir, open_port, relation_set
from charms.reactive import hook, when, when_not, set_state

import charms.apt

@hook('upgrade-charm')
def upgrade_charm():
    """Upgrade Charm"""
    hookenv.log("Upgrading REST2JFed Charm")
    try:
        subprocess.check_output(['sudo', 'service', 'rest2jfed', 'stop'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        # we do not need to exit here
    install()

@when('java.installed')
@when_not('apt.installed.python-pip','rest2jfed.installed')
def pre_install():
    hookenv.log("WOLOLO Pre-install")
    charms.apt.queue_install(['python-pip'])

@when('java.installed','apt.installed.python-pip')
@when_not('rest2jfed.installed')
def install():
    """Install REST2JFed"""
    try:
        # update needed because of weird error
        hookenv.log("Installing dependencies")
        subprocess.check_output(['sudo', 'apt-get', 'update'])
        subprocess.check_output(['pip2', 'install', 'Jinja2', 'Flask', 'pyyaml', 'click', 'python-dateutil'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        exit(1)
    hookenv.log("Extracting and moving required files and folders")
    mergecopytree(charm_dir() + '/files/jfedS4', "/opt/jfedS4")
    mergecopytree(charm_dir() + '/files/rest2jfed', "/opt/rest2jfed")
    hookenv.log("Generating upstart file")
    with open(charm_dir()+'/templates/upstart.conf', 'r') as upstart_t_file:
        upstart_template = upstart_t_file.read()
    with open('/etc/init/rest2jfed.conf', 'w') as upstart_file:
        upstart_file = upstart_file.write(upstart_template)
    hookenv.log("Starting rest2jfed service")
    try:
        subprocess.check_output(['sudo', 'service', 'rest2jfed', 'start'])
    except subprocess.CalledProcessError as exception:
        hookenv.log(exception.output)
        exit(1)
    open_port(5000)
    set_state('rest2jfed.installed')

@hook('config-changed')
def config_changed():
    """Config changed"""
    hookenv.log('Reconfiguring REST2JFed')
    conf = hookenv.config()
    with open('/opt/jfedS4/tengujfed.pass', 'w+') as pass_file:
        pass_file.write(conf['emulab-cert-pass'])
        pass_file.truncate()
    with open('/opt/jfedS4/tengujfed.pem', 'w+') as pemfile:
        pemfile.write(base64.b64decode(conf['emulab-cert']))
        pemfile.truncate()

@hook('rest2jfed-relation-changed')
def rest2jfed_relation_changed():
    """ Sets hostname and port on relation """
    hookenv.log('Reconfiguring REST2JFed relation')
    host = hookenv.unit_public_ip()
    port = '5000'
    relation_set(host=host)
    relation_set(port=port)

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
