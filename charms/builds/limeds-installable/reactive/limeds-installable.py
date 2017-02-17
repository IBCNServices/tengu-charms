#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import yaml

from charmhelpers.core.hookenv import status_set, config

from charms.reactive import (
    when,
    when_not,
    set_state,
    remove_state, )

from charms.layer import limeds  # pylint: disable=E0611,E0401


@when_not('limeds.available')
def no_limeds_connected():
    status_set(
        'waiting',
        'Waiting for LimeDS to become available.')
    remove_state('limeds.installable.deployed')


@when(
    'limeds.available')
@when_not(
    'limeds.installable.deployed')
def add_installable(limeds_relation):
    safe_deploy_installables(limeds_relation.url)


@when(
    'limeds.available',
    'limeds.installable.deployed',
    'config.changed', )
def re_add_installable(limeds_relation):
    safe_deploy_installables(limeds_relation.url)


def safe_deploy_installables(base_url):
    try:
        deploy_installables(base_url)
    except (limeds.LimeDSException, yaml.YAMLError, ValueError, TypeError) as ex:
        status_set('blocked', 'Calls failed! Is the config correct? Output: {}'.format(str(ex)))


def deploy_installables(base_url):
    limeds_sidecar = limeds.LimeDS(base_url)
    conf = config()
    installables = yaml.safe_load(conf.get("installables"))
    numinst = 0
    for installable in installables:
        numinst += 1
        (installable_id, installable_version) = installable.split(':')
        limeds_sidecar.add_installable(installable_id, installable_version)
    numsegs = 0
    segments = yaml.safe_load(conf.get("segments"))
    for segment in segments:
        numsegs += 1
        for factory, segment_config in segment.items():
            limeds_sidecar.add_segment(factory, segment_config)
    status_set('active', 'Ready ({} installables, {} segments)'.format(numinst, numsegs))
    set_state('limeds.installable.deployed')
