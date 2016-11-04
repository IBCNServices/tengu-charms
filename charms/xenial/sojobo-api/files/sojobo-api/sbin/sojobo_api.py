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
from distutils.util import strtobool

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
