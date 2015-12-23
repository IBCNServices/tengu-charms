#!/usr/bin/env python
#pylint: disable=c0111,c0301,c0103
from flask import Flask, Response, request
import requests
#import base64

APP = Flask(__name__)


@APP.route('/')
def api_root():
    """ Welcome message """
    return 'Welcome to tengu-api v0.1'


@APP.route('/tengu/hauchiwa/<instance_id>', methods=['PUT'])
def api_hauchiwa_create(instance_id):
    url = 'http://192.168.14.154:5000/hauchiwa/{}'.format(instance_id)
    headers = dict(request.headers)
    body = request.data
    resp = requests.put(url, headers=headers, data=body)
    print('debug: received: ' + str(resp))
    return (resp.text, resp.status_code, resp.headers.items())


@APP.route('/tengu/hauchiwa/<instance_id>', methods=['GET'])
def api_hauchiwa_status(instance_id):
    url = 'http://192.168.14.154:5000/hauchiwa/{}'.format(instance_id)
    headers = dict(request.headers)
    body = request.data
    resp = requests.get(url, headers=headers, data=body)
    print('debug: received: ' + str(resp))
    return (resp.text, resp.status_code, resp.headers.items())


@APP.route('/tengu/hauchiwa', methods=['GET'])
def api_hauchiwa():
    url = 'http://192.168.14.154:5000/hauchiwa'
    headers = dict(request.headers)
    body = request.data
    resp = requests.get(url, headers=headers, data=body)
    print('debug: received: ' + str(resp))
    return (resp.text, resp.status_code, resp.headers.items())


if __name__ == '__main__':
    APP.run(host='0.0.0.0')
