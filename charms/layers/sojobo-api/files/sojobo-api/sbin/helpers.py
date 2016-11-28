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
# !/usr/bin/env python3 -- before upload to github, prepend file
import json
import socket
import yaml
from os.path import expanduser

from flask import Response, request, abort

from pygments import highlight, lexers, formatters
from controllers.maas import maas_create_user, maas_get_user_api_key, maas_list_users
from juju import juju_create_user


def write_yaml(path, content):
    with open(path, "w") as y_file:
        y_file.write(yaml.dump(content))


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


def authenticate(auth, username, modelname=None):
    if username != auth.username:
        return abort(403, {'message':"Auth failed! username in auth and in url have to be the same"})
    if not auth.username in maas_list_users():
        maas_create_user(auth.username, auth.password)
        juju_create_user(auth.username, auth.password)
    token = Token()
    token.username = auth.username
    token.password = auth.password
    token.api_key = maas_get_user_api_key(token.username, auth.password)
    if modelname:
        token.modelname = "{}-{}".format(auth.username, modelname)
        token.fqmodelname = "admin/{}".format(token.modelname)
    return token


def get_controllers(name):
    with open(expanduser('~/.local/share/juju/controllers.yaml'))as c_file:
        c_contents = yaml.safe_load(c_file)
    return {
        'controllers': {
            name : c_contents['controllers'][name]
        }
    }


class Token(object):
    def __init__(self):
        self.username = None
        self.password = None
        self.api_key = None
        self.modelname = None
        self.fqmodelname = None
