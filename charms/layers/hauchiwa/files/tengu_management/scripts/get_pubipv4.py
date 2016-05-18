#!/usr/bin/python
# Copyright (C) 2016  Ghent University
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
# pylint:disable=c0111,c0301,c0325,c0103

import xml.etree.ElementTree as elementtree
import subprocess

manifest = subprocess.check_output("geni-get manifest", shell=True)
nodename = subprocess.check_output("geni-get client_id", shell=True).strip()

namespaces = {'ns': 'http://www.geni.net/resources/rspec/3', 'emulab': 'http://www.protogeni.net/resources/rspec/ext/emulab/1'}
root = elementtree.fromstring(manifest)
pubipv4 = root.find(".//emulab:routable_pool/[@client_id='pubipv4-{}']emulab:ipv4".format(nodename), namespaces)
if pubipv4 is not None:
    print('{} netmask {}'.format(pubipv4.get('address'), pubipv4.get('netmask')))
