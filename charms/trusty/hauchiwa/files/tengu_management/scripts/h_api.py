#!/usr/bin/env python
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
# pylint: disable=c0111,c0301,c0325
import os
import json
import socket
import tempfile
import subprocess
from subprocess import CalledProcessError
from distutils.util import strtobool

from pygments import highlight, lexers, formatters
from flask import Flask, Response, request, redirect, g
from oauth2client.crypt import AppIdentityError
from oauth2client.client import verify_id_token
from jujuhelpers import JujuEnvironment, JujuException, JujuNotFoundException, Service

#
# Init feature flags and global variables
#
# Docs:
# - https://flask-featureflags.readthedocs.io/en/latest/
# - http://groovematic.com/2014/10/feature-flags-in-flask/
# - http://zurb.com/forrst/posts/Feature_Flags_in_python-ulC
#
def parse_flags_from_environment(flags):
    """Creates a global bool variable for each name in `flags`.
    The value of the global variable is
     - `True` if an environment variable with the same name exists and is interpreted as True (by strtobool(value.lower())).
     - `False` in any other case
    """
    for flagname in flags:
        value = False
        try:
            value = strtobool(os.environ.get(flagname, 'False').lower())
        except ValueError:
            pass
        globals()[flagname] = value
DEBUG = False
FEATURE_FLAG_AUTH = False
parse_flags_from_environment(['DEBUG', 'FEATURE_FLAG_AUTH'])

CLIENT_ID = "186954744080-m8egj67pube80m9edfpf8isj4kn3lu38.apps.googleusercontent.com"


#
# Init flask
#
APP = Flask(__name__)
APP.url_map.strict_slashes = False

if FEATURE_FLAG_AUTH:
    @APP.before_request
    def tengu_auth():
        id_token = request.headers.get('id-token', None)
        # Check that the ID Token is valid.
        if id_token:
            try:
                # Client library can verify the ID token.
                jwt = verify_id_token(id_token, CLIENT_ID)
                g.gplus_id = jwt['sub'] # add id to request context
                return
            except AppIdentityError:
                pass
        return create_response(401, "Invalid ID Token")

@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,emulab-s4-cert,Location,id-token'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT'
    response.headers['Accept'] = 'application/json'
    return response

@APP.errorhandler(JujuNotFoundException)
def handle_invalid_usage(error):
    return create_response(404, {"msg": 'Cannot find resource. Reason: {}'.format(error.message)})

#
# Controllers
#

@APP.route('/')
def api_root():
    """ Welcome message """
    id_status = {}
    # Check that the ID Token is valid.
    if FEATURE_FLAG_AUTH:
        if g.gplus_id:
            # Client library can verify the ID token.
            id_status['valid'] = True
            id_status['gplus_id'] = g.gplus_id
            id_status['message'] = 'ID Token is valid.'
        else:
            id_status['valid'] = False
            id_status['gplus_id'] = None
            id_status['message'] = 'Invalid ID Token.'

    info = {
        "name":socket.gethostname(),
        "models": JujuEnvironment.list_environments(),
        "version": "1.1.0", # see http://semver.org/
        "request-id-token-status": id_status,
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
            output = subprocess.check_output(['tengu', 'create', '--bundle', bundle_path, modelname])
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


@APP.route('/<modelname>/<servicename>/config', methods=['GET'])
def api_service_config(modelname, servicename):
    """ Shows the info of the specified Hauchiwa instance """
    juju = JujuEnvironment(modelname)
    service = Service(servicename, juju)
    info = service.config
    return create_response(200, info)


@APP.route('/<modelname>/<servicename>/config', methods=['PUT'])
def api_service_config_change(modelname, servicename):
    """ Change config of specified hauchiwa """
    config = request.json
    juju = JujuEnvironment(modelname)
    service = Service(servicename, juju)
    try:
        service.set_config(config)
    except JujuException as exception:
        print(exception.message)
        return create_response(500, {"msg":'config change failed', "output": exception.message})
    return create_response(200, {"msg":'Config change requested'})


@APP.route('/<modelname>/<servicename>/upgrade', methods=['GET'])
def upgrade(modelname, name):
    """ Shows the status of this hauchiwa instance """
    env = JujuEnvironment(modelname)
    service = Service(name, env)
    service.upgrade()
    return create_response(200, {"msg":'Started upgrade of service {}'.format(name)})


#
# Helpers
#
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

#
# Run flask server when file is executed
#
if __name__ == '__main__':
    APP.run(host='0.0.0.0', debug=DEBUG, threaded=True)
