# Copyright 2015-2016 Canonical Ltd.
#
# This file is part of the Apt layer for Juju.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
charms.reactive helpers for dealing with deb packages.

Add apt package sources using add_source(). Queue deb packages for
installation with install(). Configure and work with your software
once the apt.installed.{packagename} state is set.
'''
import itertools
import subprocess

from charmhelpers import fetch
from charmhelpers.core import hookenv, unitdata
from charms import reactive


__all__ = ['add_source', 'update', 'queue_install', 'install_queued',
           'installed', 'purge', 'ensure_package_status']


def add_source(source, key=None):
    '''Add an apt source.

    Sets the apt.needs_update state.

    A source may be either a line that can be added directly to
    sources.list(5), or in the form ppa:<user>/<ppa-name> for adding
    Personal Package Archives, or a distribution component to enable.

    The package signing key should be an ASCII armoured GPG key. While
    GPG key ids are also supported, the retrieval mechanism is insecure.
    There is no need to specify the package signing key for PPAs or for
    the main Ubuntu archives.
    '''
    # Maybe we should remember which sources have been added already
    # so we don't waste time re-adding them. Is this time significant?
    fetch.add_source(source, key)
    reactive.set_state('apt.needs_update')


def queue_install(packages, options=None):
    """Queue one or more deb packages for install.

    The `apt.installed.{name}` state is set once the package is installed.

    If a package has already been installed it will not be reinstalled.

    If a package has already been queued it will not be requeued, and
    the install options will not be changed.

    Sets the apt.queued_installs state.
    """
    # Filter installed packages.
    store = unitdata.kv()
    queued_packages = store.getrange('apt.install_queue.', strip=True)
    packages = {package: options for package in packages
                if not (package in queued_packages or
                        reactive.helpers.is_state('apt.installed.' + package))}
    if packages:
        unitdata.kv().update(packages, prefix='apt.install_queue.')
        reactive.set_state('apt.queued_installs')


def installed():
    '''Return the set of deb packages completed install'''
    return set(state.split('.', 2)[2] for state in reactive.bus.get_states()
               if state.startswith('apt.installed.'))


def purge(packages):
    """Purge one or more deb packages from the system"""
    fetch.apt_purge(packages, fatal=True)
    store = unitdata.kv()
    store.unsetrange(packages, prefix='apt.install_queue.')
    for package in packages:
        reactive.remove_state('apt.installed.{}'.format(package))


def update():
    """Update the apt cache.

    Removes the apt.needs_update state.
    """
    status_set(None, 'Updating apt cache')
    fetch.apt_update(fatal=True)  # Friends don't let friends set fatal=False
    reactive.remove_state('apt.needs_update')


def install_queued():
    '''Installs queued deb packages.

    Removes the apt.queued_installs state and sets the apt.installed state.

    On failure, sets the unit's workload state to 'blocked' and returns
    False. Package installs remain queued.

    On success, sets the apt.installed.{packagename} state for each
    installed package and returns True.
    '''
    store = unitdata.kv()
    queue = sorted((options, package)
                   for package, options in store.getrange('apt.install_queue.',
                                                          strip=True).items())

    installed = set()
    for options, batch in itertools.groupby(queue, lambda x: x[0]):
        packages = [b[1] for b in batch]
        try:
            status_set(None, 'Installing {}'.format(','.join(packages)))
            fetch.apt_install(packages, options, fatal=True)
            store.unsetrange(packages, prefix='apt.install_queue.')
            installed.update(packages)
        except subprocess.CalledProcessError:
            status_set('blocked',
                       'Unable to install packages {}'
                       .format(','.join(packages)))
            return False  # Without setting reactive state.

    for package in installed:
        reactive.set_state('apt.installed.{}'.format(package))

    reactive.remove_state('apt.queued_installs')
    return True


def ensure_package_status():
    '''Hold or unhold packages per the package_status configuration option.

    All packages installed using this module and handlers are affected.

    An mechanism may be added in the future to override this for a
    subset of installed packages.
    '''
    packages = installed()
    if not packages:
        return
    config = hookenv.config()
    package_status = config['package_status']
    changed = reactive.helpers.data_changed('apt.package_status',
                                            (package_status, sorted(packages)))
    if changed:
        if package_status == 'hold':
            hookenv.log('Holding packages {}'.format(','.join(packages)))
            fetch.apt_hold(packages)
        else:
            hookenv.log('Unholding packages {}'.format(','.join(packages)))
            fetch.apt_unhold(packages)
    reactive.remove_state('apt.needs_hold')


def status_set(state, message):
    """Set the unit's workload status.

    Set state == None to keep the same state and just change the message.
    """
    if state is None:
        state = hookenv.status_get()[0]
        if state == 'unknown':
            state = 'maintenance'  # Guess
    if state in ('error', 'blocked'):
        lvl = hookenv.WARNING
    else:
        lvl = hookenv.INFO
    hookenv.status_set(state, message)
    hookenv.log('{}: {}'.format(state, message), lvl)
