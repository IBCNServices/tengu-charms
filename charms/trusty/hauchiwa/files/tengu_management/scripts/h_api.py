#!/usr/bin/env python
#pylint: disable=c0111,c0301
import tempfile
import json
import subprocess

from flask import Flask, Response, request


from jujuhelpers import JujuEnvironment

APP = Flask(__name__)
DEFAULT_PUBKEYS = 'ssh-rsa AAAAB3NzaC1yc2EAAAABJQAAAIEAiF+Y54T4MySG8akVwolplZoo8+uGdWHMQtzNEwbirqW8tutHmH2osYavsWyAuIbJPMH/mEMpvWNRilqXv7aw43YcD2Ie43MiLuEV6xWuC1SwdxxfyQ7Y2e0JEKohl6Xx3lWgHpiR5EZFeJmwHazthJnt94m/mTP7sEweK1m9cbk= thomasvanhove,ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2AvnkZTypu/srnyAdjHjk6x+vsre05NOwFIOieu2mcAb4aJZOLHBqEE1pxxWrvPUULFS066xgNgvKwNZOZh+OPlUdFpjY2AqN8CtNnLuQ72EPYjpV69nrtsKaJO+ZYqTnl4uZOZDeSoqK0v6RBuBfb5YcZfqpR/z/turw5yZ1H5Ju5mykhzy5wBtWMXWjnODI309Q//0+0MZTSJIYDJ05mwkM0ma1kNWEpJCw9nAvADqYZdU/8thX2j1f3KFdfupZuDIw+rvX3KgCb1cRYvfr8N165J209lxxkwJQuSVGRZ3wUytC/JkqJB1ZK5FhL9WoKD0yXDxi+5nmAQVpVPgD merlijnsebrechts'

@APP.route('/')
def api_root():
    """ Welcome message """
    return 'Welcome to Hauchiwa API v0.1'


@APP.route('/bundle', methods=['POST'])
def api_bundle_create():
    """ Deploys new bundle """
    #TODO: Authenticate this action
    # Get request values
    bundle = request.get_data()
    #s4_cert = str(request.headers.get('emulab-s4-cert'))
    # Get Instance ID
    import socket
    instance_id = socket.gethostname().lstrip('h-')
    # Write bundle
    bundle_path = tempfile.mkdtemp() + '/bundle.yaml'
    with open(bundle_path, 'w+') as bundle_file:
        bundle_file.write(bundle)
    # Run bundle
    output = subprocess.check_output(['/opt/tengu/scripts/tengu.py', 'create', '--bundle', bundle_path, instance_id])
    resp = Response(
        "Sucessfully deployed bundle to environment {}. Output: {}".format(instance_id, output),
        status=200,
        mimetype='text/plain',
    )
    return resp


@APP.route('/status', methods=['GET'])
def api_info():
    """ Shows the status of this hauchiwa instance """
    # get values from request
    #TODO: Authenticate this action
    #s4_cert = str(request.headers.get('emulab-s4-cert'))
    env = JujuEnvironment(None)
    info = env.status
    if info:
        resp = Response(
            json.dumps(info),
            status=200,
            mimetype='application/json',
        )
    else:
        resp = Response(
            "Environment {} doesn't exist or isn't bootstrapped".format(env.name),
            status=404,
            mimetype='text/plain',
        )
    return resp


if __name__ == '__main__':
    APP.run(host='0.0.0.0')
