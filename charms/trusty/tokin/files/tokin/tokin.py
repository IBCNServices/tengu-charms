#!/usr/bin/env python
#pylint: disable=c0111,c0301
from flask import Flask, Response, request
import tempfile
import yaml
import json
from jujuhelpers import JujuEnvironment
#import base64

APP = Flask(__name__)
DEFAULT_PUBKEYS = 'ssh-rsa AAAAB3NzaC1yc2EAAAABJQAAAIEAiF+Y54T4MySG8akVwolplZoo8+uGdWHMQtzNEwbirqW8tutHmH2osYavsWyAuIbJPMH/mEMpvWNRilqXv7aw43YcD2Ie43MiLuEV6xWuC1SwdxxfyQ7Y2e0JEKohl6Xx3lWgHpiR5EZFeJmwHazthJnt94m/mTP7sEweK1m9cbk= thomasvanhove,ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2AvnkZTypu/srnyAdjHjk6x+vsre05NOwFIOieu2mcAb4aJZOLHBqEE1pxxWrvPUULFS066xgNgvKwNZOZh+OPlUdFpjY2AqN8CtNnLuQ72EPYjpV69nrtsKaJO+ZYqTnl4uZOZDeSoqK0v6RBuBfb5YcZfqpR/z/turw5yZ1H5Ju5mykhzy5wBtWMXWjnODI309Q//0+0MZTSJIYDJ05mwkM0ma1kNWEpJCw9nAvADqYZdU/8thX2j1f3KFdfupZuDIw+rvX3KgCb1cRYvfr8N165J209lxxkwJQuSVGRZ3wUytC/JkqJB1ZK5FhL9WoKD0yXDxi+5nmAQVpVPgD merlijnsebrechts'

@APP.route('/')
def api_root():
    """ Welcome message """
    return 'Welcome to tokin v0.1'


@APP.route('/hauchiwa/<instance_id>', methods=['PUT'])
def api_hauchiwa_create(instance_id):
    """ Creates new tengu hauchiwa """
    if len(instance_id) > 10:
        return Response("instance_id cannot be longer than 10 characters",
                        status=400,
                        mimetype='text/plain')
    # get values from request
    s4_cert = str(request.headers.get('emulab-s4-cert'))
    ssh_keys = request.form.get('ssh-keys')
    # Create config file
    hauchiwa_name = 'h-{}'.format(instance_id)
    hauchiwa_cfg = {
        str(hauchiwa_name):{
            'emulab-s4-cert' : s4_cert,
            'emulab-project-name' : "tengu",
            'charm-repo-source' : "https://github.com/galgalesh/tengu-charms.git",
            'ssh-keys' : str(','.join([DEFAULT_PUBKEYS, ssh_keys])),
        }
    }
    hauchiwa_cfg_path = tempfile.mkdtemp() + 'hauchiwa-cfg.yaml'
    with open(hauchiwa_cfg_path, 'w+') as hauchiwa_cfg_file:
        hauchiwa_cfg_file.write(yaml.dump(hauchiwa_cfg, default_flow_style=False))
    # Deploy Hauchiwa
    juju = JujuEnvironment(None)
    juju.deploy('local:hauchiwa',
                hauchiwa_name,
                config_path=hauchiwa_cfg_path,
                to='lxc:1')
    juju.add_relation(hauchiwa_name, 'rest2jfed')
    resp = Response(
        "Created hauchiwa instance {}".format(instance_id),
        status=201,
        mimetype='text/plain',
    )
    resp.headers['location'] = '/hauchiwa/{}'.format(instance_id)

    return resp


@APP.route('/hauchiwa/<instance_id>', methods=['GET'])
def api_hauchiwa_info(instance_id):
    """ Shows the info of the specified Hauchiwa instance """
    if len(instance_id) > 10:
        return Response("instance_id cannot be longer than 10 characters",
                        status=400,
                        mimetype='text/plain')
    # get values from request
    #TODO: Authenticate this action
    #s4_cert = str(request.headers.get('emulab-s4-cert'))
    juju = JujuEnvironment(None)
    info = juju.status['services'].get('h-{}'.format(instance_id))
    if info:
        info = {
            'status' : info['service-status'],
            'public-address' : info['units'].values()[0].get('public-address')
        }
        resp = Response(
            json.dumps(info),
            status=200,
            mimetype='application/json',
        )
    else:
        resp = Response(
            'Cannot find instance {}'.format(instance_id),
            status=404,
            mimetype='text/plain',
        )


    resp.headers['location'] = '/hauchiwa/{}'.format(instance_id)

    return resp


# @APP.route('/hauchiwa/<instance_id>', methods=['DELETE'])
# def api_hauchiwa_destroy(instance_id):
#     """ Deletes tengu hauchiwa """
#     if len(instance_id) > 10:
#         return Response("instance_id cannot be longer than 10 characters",
#                         status=400,
#                         mimetype='text/plain')
#     juju = JujuEnvironment(None)
#     hauchiwa_name = instance_id + '-hauchiwa'
#     juju.destroy_service(tia_name)


if __name__ == '__main__':
    APP.run(host='0.0.0.0')
