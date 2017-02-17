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
import jinja2

from charmhelpers.core.hookenv import status_set, config, charm_dir

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


@when_not('influxdb.available')
def no_influxdb_connected():
    status_set(
        'blocked',
        'Waiting for connection to InfluxDB.')
    remove_state('limeds.installable.deployed')


@when(
    'limeds.available',
    'influxdb.available', )
@when_not(
    'limeds.installable.deployed')
def add_installable(limeds_relation, influxdb_relation):
    deploy_installable(limeds_relation.url, influxdb_relation.hostname(), influxdb_relation.port())


@when(
    'limeds.available',
    'influxdb.available',
    'limeds.installable.deployed',
    'config.changed', )
def re_add_installable(limeds_relation, influxdb_relation):
    deploy_installable(limeds_relation.url, influxdb_relation.hostname(), influxdb_relation.port())


def deploy_installable(base_url, influx_hostname, influx_port):
    limeds_sidecar = limeds.LimeDS(base_url)
    conf = config()
    installable_id = conf.get('installable-id')
    installable_version = conf.get('installable-version')
    factory_id = conf.get('installable-id') + ".Factory"
    with open("{}/templates/influxdb-config.json".format(charm_dir()), 'r') as conf_file:
        conf_template = jinja2.Template(conf_file.read())
    segment_config = conf_template.render(
        segment_id=conf.get('segment-id'),
        database=conf.get('database'),
        host=influx_hostname,
        port=influx_port, )

    limeds_sidecar.add_installable(installable_id, installable_version)
    limeds_sidecar.add_segment(factory_id, segment_config)

    status_set('active', 'Ready ({})'.format(conf.get('segment-id')))
    set_state('limeds.installable.deployed')
