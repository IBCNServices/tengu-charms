#!/usr/bin/env python
#pylint: disable=c0111,c0301
import os
import json
import socket
import tempfile
import subprocess
from subprocess import CalledProcessError

from flask import Flask, Response, request, redirect
from pygments import highlight, lexers, formatters

from jujuhelpers import JujuEnvironment, JujuNotFoundException, Service


APP = Flask(__name__)


@APP.route('/')
def api_root():
    """ Welcome message """
    info = {
        "name":socket.gethostname(),
        "models": JujuEnvironment.list_environments(),
    }
    return create_response(200, info)


@APP.route('/favicon.ico')
def api_icon():
    """ icon """
    return redirect("http://tengu.io/assets/icons/favicon.ico", code=302)


@APP.route('/<modelname>/', methods=['GET'])
def api_model_info(modelname):
    """ Shows the status of this hauchiwa instance """
    env = JujuEnvironment(modelname)
    info = env.status
    if info:
        return create_response(200, info)


@APP.route('/<modelname>/', methods=['PUT'])
def api_model_update(modelname):
    """ Deploys new bundle """
    bundle = request.data
    # Write bundle
    bundle_path = tempfile.mkdtemp() + '/bundle.yaml'
    with open(bundle_path, 'w+') as bundle_file:
        bundle_file.write(bundle)
    # Create environment from bundle if not exist, else deploy bundle
    if JujuEnvironment.env_exists(modelname):
        env = JujuEnvironment(modelname)
        output = env.deploy_bundle(bundle_path, '--skip-unit-wait')
    else:
        try:
            output = subprocess.check_output(['/opt/tengu/scripts/tengu.py', 'create', '--bundle', bundle_path, modelname])
        except CalledProcessError as process_error:
            return create_response(500, {"msg": "Failed to deploy bundle to environment {}. Output: {}".format(modelname, process_error.output)})
    return create_response(200, {"msg": "Sucessfully deployed bundle to environment {}. Output: {}".format(modelname, output)})


@APP.route('/<modelname>/<servicename>', methods=['GET'])
def api_service_info(modelname, servicename):
    """ Shows the info of the specified Hauchiwa instance """
    juju = JujuEnvironment(modelname)
    service = Service(servicename, juju)
    info = service.status
    return create_response(200, info)



@APP.route('/<modelname>/<servicename>/upgrade', methods=['GET'])
def upgrade(modelname, name):
    """ Shows the status of this hauchiwa instance """
    env = JujuEnvironment(modelname)
    service = Service(name, env)
    service.upgrade()
    return create_response(200, {"msg":'Started upgrade of service {}'.format(name)})


def create_response(http_code, return_object):
    if request_wants_json():
        return Response(
            json.dumps(return_object),
            status=http_code,
            mimetype='application/json',
        )
    else:
        formatted_json = json.dumps(return_object, indent=4)
        formatter = formatters.HtmlFormatter( #pylint: disable=E1101
            full=True,
            title="{} returns:".format(socket.gethostname())
        )
        colorful_json = highlight(unicode(formatted_json, 'UTF-8'), lexers.JsonLexer(), formatter) # pylint: disable=E1101
        return Response(
            colorful_json,
            status=http_code,
            mimetype='text/html',
        )


def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,emulab-s4-cert,Location'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT'
    response.headers['Accept'] = 'application/json'
    return response


@APP.errorhandler(JujuNotFoundException)
def handle_invalid_usage(error):
    return create_response(404, {"msg": 'Cannot find resource. Reason: {}'.format(error.message)})


if __name__ == '__main__':
    DEBUG = (os.environ.get('DEBUG', 'False').lower() == 'true')
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
