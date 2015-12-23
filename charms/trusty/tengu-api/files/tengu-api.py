#!/usr/bin/env python
#pylint: disable=c0111,c0301
from flask import Flask, Response, request
#import base64

APP = Flask(__name__)


@APP.route('/')
def api_root():
    """ Welcome message """
    return 'Welcome to tengu-api v0.1'


@APP.route('/hauchiwa/<instance_id>', methods=['PUT'])
def api_hauchiwa_create(instance_id):
    """ Creates new tengu hauchiwa """
    if len(instance_id) > 10:
        return Response("instance_id cannot be longer than 10 characters",
                        status=400,
                        mimetype='text/plain')
    # get values from request
    s4_cert = str(request.headers.get('emulab-s4-cert'))
    ssh_keys = request.form.get('ssh-keys', default="")
    # Create config file
    return


if __name__ == '__main__':
    APP.run(host='0.0.0.0')
