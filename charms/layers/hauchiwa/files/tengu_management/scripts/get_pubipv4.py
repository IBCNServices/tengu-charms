#!/usr/bin/python
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
