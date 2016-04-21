#!/usr/bin/env python
#pylint: disable=c0111,c0301
import os
import json
import tempfile
import subprocess

from flask import Flask, Response, request
from pygments import highlight, lexers, formatters


from jujuhelpers import JujuEnvironment, Service

APP = Flask(__name__)
DEFAULT_PUBKEYS = 'ssh-rsa AAAAB3NzaC1yc2EAAAABJQAAAIEAiF+Y54T4MySG8akVwolplZoo8+uGdWHMQtzNEwbirqW8tutHmH2osYavsWyAuIbJPMH/mEMpvWNRilqXv7aw43YcD2Ie43MiLuEV6xWuC1SwdxxfyQ7Y2e0JEKohl6Xx3lWgHpiR5EZFeJmwHazthJnt94m/mTP7sEweK1m9cbk= thomasvanhove,ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2AvnkZTypu/srnyAdjHjk6x+vsre05NOwFIOieu2mcAb4aJZOLHBqEE1pxxWrvPUULFS066xgNgvKwNZOZh+OPlUdFpjY2AqN8CtNnLuQ72EPYjpV69nrtsKaJO+ZYqTnl4uZOZDeSoqK0v6RBuBfb5YcZfqpR/z/turw5yZ1H5Ju5mykhzy5wBtWMXWjnODI309Q//0+0MZTSJIYDJ05mwkM0ma1kNWEpJCw9nAvADqYZdU/8thX2j1f3KFdfupZuDIw+rvX3KgCb1cRYvfr8N165J209lxxkwJQuSVGRZ3wUytC/JkqJB1ZK5FhL9WoKD0yXDxi+5nmAQVpVPgD merlijnsebrechts'

@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,emulab-s4-cert,Location'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT'
    response.headers['Accept'] = 'application/json'
    return response


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
    output = subprocess.check_call(['/opt/tengu/scripts/tengu.py', 'create', '--bundle', bundle_path, instance_id])
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
        if request_wants_json():
            resp = Response(
                json.dumps(info),
                status=200,
                mimetype='application/json',
            )
        else:
            formatted_json = json.dumps(info, indent=4)
            colorful_json = highlight(unicode(formatted_json, 'UTF-8'), lexers.JsonLexer(), formatters.HtmlFormatter(full=True)) # pylint: disable=E1101
            resp = Response(
                colorful_json,
                status=200,
                mimetype='text/html',
            )
    else:
        resp = Response(
            "Environment {} doesn't exist or isn't bootstrapped".format(env.name),
            status=404,
            mimetype='text/plain',
        )
    return resp


@APP.route('/services/<name>/upgrade', methods=['GET'])
def upgrade(name):
    """ Shows the status of this hauchiwa instance """
    # get values from request
    #TODO: Authenticate this action
    env = JujuEnvironment(None)
    service = Service(name, env)
    service.upgrade()
    resp = Response(
        'Started upgrade of service {}'.format(name),
        status=200,
        mimetype='text/plain',
    )
    return resp


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

if __name__ == '__main__':
    DEBUG = (os.environ.get('DEBUG', 'False').lower() == 'true')
    APP.run(host='0.0.0.0', debug=DEBUG)
