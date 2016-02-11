# python3
# pylint: disable=c0111,
import subprocess
import os
import shutil
import re
from tempfile import NamedTemporaryFile

from charmhelpers import fetch
from charmhelpers.core import templating, host

from charms.reactive import set_state
from charms.reactive import when, when_not, hook
from charms.reactive import hookenv
from charms.reactive.decorators import when_file_changed


@when('juju.installed')
@when_not('tokin.installed')
def install():
    set_hostname('tokin')
    install_tokin()
    set_state('tokin.installed')


def install_tokin():

    hookenv.status_set('maintenance', 'Installing tokin')
    packages = ['python-pip']
    fetch.apt_install(fetch.filter_installed_packages(packages))
    subprocess.check_output([
        'pip2', 'install', 'Jinja2', 'Flask', 'jujuclient', 'pyyaml'
    ])
    mergecopytree('files/tokin', '/opt/tokin',
                  symlinks=True)
    templating.render(
        source='upstart.conf',
        target='/etc/init/tokin.conf',
        context={}
    )


@when('tokin.ready')
@when_not('tokin.started')
def start():
    host.service_start('tokin')
    set_state('tokin.started')
    hookenv.status_set('Ready', 'Tokin ready')


# Service will restart even if files change outside of Juju.
# `update-status` hook will run periodically checking the hash of those files.
@when_file_changed(
    '/etc/init/tokin.conf',
    '/opt/tokin/tokin.py',
    '/opt/tokin/jujuhelpers.py')
@when('tokin.started')
def restart():
    host.service_restart('tokin')


@hook('upgrade-charm')
def upgrade():
    install_tokin()


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


def set_hostname(hostname):
    # set service_name as hostname
    subprocess.check_call(['hostnamectl', 'set-hostname', hostname])
    # Make hostname resolvable
    id = '# Managed by Juju set_hostname'
    remove_matches('/etc/hosts', id)
    with open('/etc/hosts', 'a') as hosts_file:
        hosts_file.write('127.0.0.1 {} {}\n'.format(hostname, id))


def remove_matches(filename, pattern):
    encoding = 'utf-8'
    matched = re.compile(pattern).search
    with open(filename, encoding=encoding) as input_file:
        with NamedTemporaryFile(mode='w', encoding=encoding,
                                dir=os.path.dirname(filename)) as outfile:
            for line in input_file:
                if not matched(line):
                    print(line, end='', file=outfile)
            outfile.delete = False # don't delete it on closing
    os.replace(outfile.name, input_file.name)
