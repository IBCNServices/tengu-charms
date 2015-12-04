#!/usr/bin/env python
#pylint: disable=c0111
from flask import Flask, Response, request
import tempfile
import yaml
from juju import JujuEnvironment
#import base64

APP = Flask(__name__)


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
    juju = JujuEnvironment(None)
    hauchiwa_name = instance_id + 'hauchiwa'
    hauchiwa_cfg = {str(hauchiwa_name):{}}
    hauchiwa_cfg[hauchiwa_name]['emulab-s4-cert'] = str(request.headers.get('emulab-s4-cert'))
    hauchiwa_cfg[hauchiwa_name]['emulab-project-name'] = "tengu"
    hauchiwa_cfg[hauchiwa_name]['charm-repo-source'] = "https://github.com/galgalesh/tengu-charms.git"
    t_dir = tempfile.mkdtemp()
    hauchiwa_cfg_path = t_dir + 'hauchiwa-cfg.yaml'
    with open(hauchiwa_cfg_path, 'w+') as hauchiwa_cfg_file:
        hauchiwa_cfg_file.write(yaml.dump(hauchiwa_cfg, default_flow_style=False))
    juju.deploy('local:hauchiwa',
                hauchiwa_name,
                config_path=hauchiwa_cfg_path,
                to='lxc:1')
    juju.add_relation(hauchiwa_name, 'rest2jfed')
    resp = Response("", status=201, mimetype='text/plain')
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
#
#
# @APP.route('/tia/<instance_id>/lambda', methods=['PUT'])
# def api_hauchiwa_deploy_lambda(instance_id):
#     """ Deploy lambda architecture on instance """
#     hnodes = request.form['hnodes']
#     snodes = request.form['snodes']
#     from bundletools.bundlecreator import create_lambda
#     bundle = create_lambda(hnodes, snodes)
#     bundleb64 = base64.b64encode(bundle)
#     unit = "{}/0".format(instance_id)
#     juju = JujuEnvironment(None)
#     output = juju.action_do(unit, 'deploy-bundle', bundle=bundleb64)
#     a_id = output.lstrip("Action queued with id: ").rstrip()
#     resp = Response("Action id: {} "
#                     "started creating bundle {}".format(a_id, bundleb64),
#                     status=203,
#                     mimetype='text/plain')
#     return resp


if __name__ == '__main__':
    APP.run(host='0.0.0.0')
