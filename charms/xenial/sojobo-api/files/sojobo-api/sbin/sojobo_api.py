#!/usr/bin/env python3
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
from subprocess import check_call
from distutils.util import strtobool

from lxml import html

import requests
from pygments import highlight, lexers, formatters
from flask import Flask, Response, request, redirect

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
parse_flags_from_environment(['DEBUG', 'FEATURE_FLAG_AUTH'])

MAAS_USER = os.environ.get('MAAS_USER')
MAAS_API_KEY = os.environ.get('MAAS_API_KEY')
MAAS_URL = os.environ.get('MAAS_URL')
check_call(['maas', 'login', MAAS_USER, MAAS_URL, MAAS_API_KEY])

#
# Init flask
#
APP = Flask(__name__)
APP.url_map.strict_slashes = False


@APP.after_request
def apply_caching(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,emulab-s4-cert,Location,id-token'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Type,Location'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT'
    response.headers['Accept'] = 'application/json'
    return response

# @APP.errorhandler(JujuNotFoundException)
# def handle_invalid_usage(error):
#     return create_response(404, {"msg": 'Cannot find resource. Reason: {}'.format(error.message)})

#
# Controllers
#

@APP.route('/')
def api_root():
    """ Welcome message """
    info = {
        "name": socket.gethostname(),
        "version": "0.0.1", # see http://semver.org/
    }
    return create_response(200, info)


@APP.route('/favicon.ico')
def api_icon():
    """ icon """
    return redirect("http://tengu.io/assets/icons/favicon.ico", code=302)


@APP.route('/users/<username>/models/<modelname>')
def create_model(username, modelname):
    if username != request.authorization.username:
        return create_response(403, {'message':"username in auth and in url have to be the same"})

    auth = authenticate(request.authorization)
    model = request.json
    modelname = "{}-{}".format(auth.username, modelname)
    juju_create_model(auth.username, auth.api_key, model['ssh-keys'], modelname)





    return create_response(200, {})

def authenticate(auth):
    if not auth.username in maas_list_users():
        maas_create_user(auth.username, auth.password)
        juju_create_user(auth.username, auth.password)
    user = object
    user.username = auth.username
    user.password = auth.password
    user.api_key = maas_get_user_api_key(auth.username, auth.password)
    return user

def maas_list_users():
    users = json.loads(subprocess.check_output(['maas', MAAS_USER, 'users', 'read'], universal_newlines=True))
    return [u['username'] for u in users]

def maas_create_user(username, password):
    # email has to be unique
    check_call(['maas', MAAS_USER, 'users', 'create', 'username={}'.format(username), 'email=merlijn.sebrechts+maas-user-{}@gmail.com'.format(username), 'password={}'.format(password), 'is_superuser=0'])

def maas_get_user_api_key(username, password):
    # source: https://stackoverflow.com/questions/11892729/how-to-log-in-to-a-website-using-pythons-requests-module/17633072#17633072
    payload = {
        'username': username,
        'password': password
    }
    with requests.Session() as session:
        login_response = session.post('http://193.190.127.161/MAAS/accounts/login/', data=payload)
        print(login_response)
        api_page_response = session.get('http://193.190.127.161/MAAS/account/prefs/')
        print(api_page_response)
    tree = html.fromstring(api_page_response.text)
    api_keys = tree.xpath('//div[@id="api"]//input/@value')
    return api_keys[-1]

def juju_list_users():
    users = json.loads(subprocess.check_output(['juju', 'list-users', '--format', 'json'], universal_newlines=True))
    return [u['user-name'] for u in users]

def juju_create_user(username, password):
    check_call(['juju', 'add-user', username])
    check_call(['juju', 'change-user-password', username], input="{}\n{}".format(password, password))

def juju_create_model(username, api_key, ssh_keys, modelname):
    credentials = {
        'credentials': {
            'maas': {
                username: {
                    'auth-type': 'oauth1',
                    'maas-oauth': api_key,
                }
            }
        }
    }
    tmp = tempfile.NamedTemporaryFile()
    tmp.write(json.dumps(credentials))
    tmp.close()  # deletes the file
    config = []
    if ssh_keys:
        config = config + ['authorized-keys="{}"'.format(ssh_keys)]
    if len(config):
        config = ['--config'] + config
    check_call(['juju', 'add-credential', '--replace', 'True', '-f', tmp.name])
    check_call(['juju', 'add-model', modelname, '--credential', username] + config)
    check_call(['juju', 'grant', username, 'admin', modelname])




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
        colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatter) # pylint: disable=E1101
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
