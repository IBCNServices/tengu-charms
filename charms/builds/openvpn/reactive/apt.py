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
import subprocess

from charmhelpers import fetch
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import WARNING
from charms import layer
from charms import reactive
from charms.reactive import when, when_not

import charms.apt


@when('apt.needs_update')
def update():
    charms.apt.update()


@when('apt.queued_installs')
@when_not('apt.needs_update')
def install_queued():
    charms.apt.install_queued()


@when_not('apt.queued_installs')
def ensure_package_status():
    charms.apt.ensure_package_status()


def filter_installed_packages(packages):
    # Don't use fetch.filter_installed_packages, as it depends on python-apt
    # and not available if the basic layer's use_site_packages option is off
    cmd = ['dpkg-query', '--show', r'--showformat=${Package}\n']
    installed = set(subprocess.check_output(cmd,
                                            universal_newlines=True).split())
    return set(packages) - installed


def clear_removed_package_states():
    """On hook startup, clear install states for removed packages."""
    removed = filter_installed_packages(charms.apt.installed())
    if removed:
        hookenv.log('{} missing packages ({})'.format(len(removed),
                                                      ','.join(removed)),
                    WARNING)
        for package in removed:
            reactive.remove_state('apt.installed.{}'.format(package))


def configure_sources():
    """Add user specified package sources from the service configuration.

    See charmhelpers.fetch.configure_sources for details.
    """
    config = hookenv.config()

    # We don't have enums, so we need to validate this ourselves.
    package_status = config.get('package_status') or ''
    if package_status not in ('hold', 'install'):
        charms.apt.status_set('blocked',
                              'Unknown package_status {}'
                              ''.format(package_status))
        # Die before further hooks are run. This isn't very nice, but
        # there is no other way to inform the operator that they have
        # invalid configuration.
        raise SystemExit(0)

    sources = config.get('install_sources') or ''
    keys = config.get('install_keys') or ''
    if reactive.helpers.data_changed('apt.configure_sources', (sources, keys)):
        fetch.configure_sources(update=False,
                                sources_var='install_sources',
                                keys_var='install_keys')
        reactive.set_state('apt.needs_update')

    # Clumsy 'config.get() or' per Bug #1641362
    extra_packages = sorted((config.get('extra_packages') or '').split())
    if extra_packages:
        charms.apt.queue_install(extra_packages)


def queue_layer_packages():
    """Add packages listed in build-time layer options."""
    # Both basic and apt layer. basic layer will have already installed
    # its defined packages, but rescheduling it here gets the apt layer
    # state set and they will pinned as any other apt layer installed
    # package.
    opts = layer.options()
    for section in ['basic', 'apt']:
        if section in opts and 'packages' in opts[section]:
            charms.apt.queue_install(opts[section]['packages'])


# Per https://github.com/juju-solutions/charms.reactive/issues/33,
# this module may be imported multiple times so ensure the
# initialization hook is only registered once. I have to piggy back
# onto the namespace of a module imported before reactive discovery
# to do this.
if not hasattr(reactive, '_apt_registered'):
    # We need to register this to run every hook, not just during install
    # and config-changed, to protect against race conditions. If we don't
    # do this, then the config in the hook environment may show updates
    # to running hooks well before the config-changed hook has been invoked
    # and the intialization provided an opertunity to be run.
    hookenv.atstart(hookenv.log, 'Initializing Apt Layer')
    hookenv.atstart(clear_removed_package_states)
    hookenv.atstart(configure_sources)
    hookenv.atstart(queue_layer_packages)
    hookenv.atstart(charms.apt.reset_application_version)
    reactive._apt_registered = True
