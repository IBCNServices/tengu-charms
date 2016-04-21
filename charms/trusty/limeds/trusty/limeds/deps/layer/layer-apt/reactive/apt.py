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
from charmhelpers import fetch
from charmhelpers.core import hookenv
from charms import reactive
from charms.reactive import when, when_not

import charms.apt
# Aliases for backwards compatibility
from charms.apt import add_source, queue_install, installed, purge


__all__ = ['add_source', 'update', 'queue_install', 'install_queued',
           'installed', 'purge', 'ensure_package_status']


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


def configure_sources():
    """Add user specified package sources from the service configuration.

    See charmhelpers.fetch.configure_sources for details.
    """
    hookenv.log('Initializing Apt Layer')
    config = hookenv.config()

    # We don't have enums, so we need to validate this ourselves.
    package_status = config.get('package_status')
    if package_status not in ('hold', 'install'):
        charms.apt.status_set('blocked',
                              'Unknown package_status {}'
                              ''.format(package_status))
        # Die before further hooks are run. This isn't very nice, but
        # there is no other way to inform the operator that they have
        # invalid configuration.
        raise SystemExit(0)

    sources = config.get('install_sources')
    keys = config.get('install_keys')
    if reactive.helpers.data_changed('apt.configure_sources', (sources, keys)):
        fetch.configure_sources(update=False,
                                sources_var='install_sources',
                                keys_var='install_keys')
        reactive.set_state('apt.needs_update')

    extra_packages = sorted(config.get('extra_packages', '').split())
    if extra_packages:
        queue_install(extra_packages)


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
    hookenv.atstart(configure_sources)
    reactive._apt_registered = True
