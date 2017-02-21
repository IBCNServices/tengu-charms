#!/usr/bin/env python3
# Copyright (c) 2017, Ghent University
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
import json
import requests

from charmhelpers.core import hookenv
config = hookenv.config()


class LimeDSException(Exception):
    pass


class LimeDS:
    @classmethod
    def __init__(cls, base_url):
        cls.base_url = base_url

    def get_deploy_url(self, installable_id, installable_version):
        deploy_url = "{limeds_url}/_limeds/installables"\
                     "/{installable_id}/{installable_version}"\
                     "/deploy".format(
                         limeds_url=self.base_url,
                         installable_id=installable_id,
                         installable_version=installable_version)
        return deploy_url

    def get_factory_url(self, factory_id):
        factory_url = "{limeds_url}/_limeds/config"\
                      "/{factory_id}".format(
                          limeds_url=self.base_url,
                          factory_id=factory_id, )
        return factory_url

    def add_installable(self, installable_id, installable_version):
        deploy_url = self.get_deploy_url(installable_id, installable_version)
        print("configuring LimeDS, adding installable: {}".format(deploy_url))
        response = requests.get(deploy_url, headers={"Accept": "application/json"})
        print("response is:{}".format(response.text))
        if not response.status_code == 200:
            raise LimeDSException("ERROR: Deploying installable failed: {} {}".format(
                response.status_code,
                response.text))

    def add_segment(self, installable_id, segment_config):
        factory_url = self.get_factory_url(installable_id)
        print("Creating instance: {}, \n {}".format(factory_url, segment_config))
        response = requests.post(
            factory_url,
            headers={"Accept": "application/json"},
            data=segment_config, )
        print("response is:{}".format(response.text))
        if not response.status_code == 200:
            raise LimeDSException("ERROR: Creating segment failed: {} {}".format(
                response.status_code,
                response.text))


def get_segment_id_from_config(config_str):
    try:
        conf = json.loads(config_str)
        for conf_value_dict in conf:
            if conf_value_dict['name'] == "$.id":
                return conf_value_dict['value']
    except ValueError:
        pass
    return None
