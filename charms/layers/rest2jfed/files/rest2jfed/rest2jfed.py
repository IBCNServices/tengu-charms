#!/usr/bin/env python
#pylint:disable=C0301
""" REST server that calls the jfed_cli tool """
from flask import Flask, Response, request
import tempfile
import base64
import os
import json
import time
import shutil
# Custom modules
from jfed_utils import JFed, JfedError, NotExistError

APP = Flask(__name__)


PROPERTIES_PATH = '/opt/jfedS4/context_tengujfed_wall2.properties'
ARCHIVE_PATH = '/opt/rest2jfed/archive'
DEFAULT_RSPEC_PATH = '/opt/rest2jfed/node.rspec'


@APP.route('/')
def api_root():
    """ Info message """
    return 'Welcome to rest2jfed python flask implementation 0.1'


@APP.route('/userinfo', methods=['GET'])
def api_userinfo():
    """ Returns the info of the user """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    jfed = JFed(None,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    odict = jfed.get_userinfo()
    resp = Response(json.dumps(odict),
                    status=200,
                    mimetype='text/plain')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>', methods=['POST'])
def api_slice_create(projectname, slicename):
    """ Creates new jfed slice using s4 certificate"""
    # Get request values
    rspec = request.get_data()
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    rspec_path = t_dir + '/rspec.rspec'
    cert_path = t_dir + '/s4.cert.xml'
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    with open(rspec_path, 'w+') as rspec_f:
        rspec_f.write(rspec)
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    # If we already have a manifest, check if experiment exists. If so, exit.
    # If not so, backup previous dir and create new experiment.
    if os.path.isdir(slice_dir) and os.path.isfile(manifest_path):
        slice_exists = jfed.slice_exists(slicename, manifest_path)
        if slice_exists:
            resp = Response("Cannot modify existing slice",
                            status=409,
                            mimetype='text/plain')
            return resp
        else:
            shutil.move(slice_dir, '{}.bak{}'.format(slice_dir, time.time()))
    os.makedirs(slice_dir)
    # Run command
    try:
        jfed.create_slice(slicename, rspec_path, manifest_path)
        with open(manifest_path, 'r') as manifest_f:
            resp = Response(manifest_f.read(),
                            status=201,
                            mimetype='application/xml')
        return resp
    except JfedError as ex:
        resp = Response(json.dumps(ex.odict),
                        status=500,
                        mimetype='application/json')
        return resp


@APP.route('/projects/<projectname>/slices/<slicename>', methods=['DELETE'])
def api_slice_destroy(projectname, slicename):
    """ Creates new jfed slice using s4 certificate"""
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create temp dir
    t_dir = tempfile.mkdtemp()
    # Populate temp dir
    cert_path = t_dir + '/s4.cert.xml'
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    # SAFETY: do not delete slice you didn't make yourself
    if not os.path.isfile(manifest_path):
        resp = Response(
            "Could not find cached manifest ({}). This server didn't create "
            "the slice so it will not delete it.".format(manifest_path),
            status=401,
            mimetype='text/plain'
        )
        return resp
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    # Run command
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    try:
        odict = jfed.delete_slice(slicename, manifest_path)
        resp = Response(json.dumps(odict),
                        status=200,
                        mimetype='application/json')
        return resp
    except JfedError as ex:
        resp = Response(json.dumps(ex.odict),
                        status=500,
                        mimetype='application/json')
        return resp


@APP.route('/projects/<projectname>/slices/<slicename>/status', methods=['GET'])
def api_slice_status(projectname, slicename):
    """ Returns the status of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    if not os.path.isfile(manifest_path):
        manifest_path = DEFAULT_RSPEC_PATH
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    # Run command
    status = jfed.get_slice_status(slicename, manifest_path)
    # Return response or error
    resp = Response(json.dumps(status),
                    status=200,
                    mimetype='application/json')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/info', methods=['GET'])
def api_slice_info(projectname, slicename):
    """ Returns the info of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    output = jfed.get_sliceinfo(slicename)
    resp = Response(json.dumps(output),
                    status=200,
                    mimetype='application/json')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/expiration', methods=['GET'])
def api_slice_expiration(projectname, slicename):
    """ Returns the status of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    if not os.path.isfile(manifest_path):
        manifest_path = DEFAULT_RSPEC_PATH
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    # Run command
    try:
        expiration = jfed.get_slice_expiration(slicename, manifest_path)
        resp = Response(json.dumps(expiration),
                        status=200,
                        mimetype='application/json')
    except NotExistError as err:
        resp = Response(json.dumps(err.odict),
                        status=404,
                        mimetype='application/json')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/expiration', methods=['GET'])
def api_slice_exists(projectname, slicename):
    """ Returns the status of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    if not os.path.isfile(manifest_path):
        manifest_path = DEFAULT_RSPEC_PATH
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    # Run command
    try:
        expiration = jfed.slice_exists(slicename, manifest_path)
        resp = Response(json.dumps(expiration),
                        status=200,
                        mimetype='application/json')
    except NotExistError as err:
        resp = Response(json.dumps(err.odict),
                        status=404,
                        mimetype='application/json')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/expiration',
           methods=['POST'])
def api_slice_renew(projectname, slicename):
    """ Renews slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    exp_hours = request.get_data()
    # Create and populate temp dir
    t_dir = tempfile.mkdtemp()
    cert_path = t_dir + '/s4.cert.xml'
    with open(cert_path, 'w+') as cert_f:
        cert_f.write(base64.b64decode(cert))
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    if not os.path.isfile(manifest_path):
        manifest_path = DEFAULT_RSPEC_PATH
    jfed = JFed(projectname,
                s4cert=cert_path,
                properties=PROPERTIES_PATH)
    # Run command
    try:
        odict = jfed.renew_slice(slicename, manifest_path, exp_hours)
        resp = Response(json.dumps(odict),
                        status=200,
                        mimetype='application/json')
        return resp
    except JfedError as ex:
        resp = Response(json.dumps(ex.odict),
                        status=500,
                        mimetype='application/json')
        return resp


@APP.route('/projects/<projectname>/slices/<slicename>', methods=['GET'])
def api_slice_manifest(projectname, slicename):
    """ Returns the manifest of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    # TODO: Find a way to authorize this action
    slice_dir = ARCHIVE_PATH+"/projects/{0}/slices/{1}".format(projectname,
                                                               slicename)
    manifest_path = slice_dir + '/manifest.mrspec'
    if os.path.isfile(manifest_path):
        with open(manifest_path, 'r') as manifest_file:
            manifest = manifest_file.read()
        resp = Response(manifest,
                        status=200,
                        mimetype='application/xml')
    else:
        resp = Response("Manifest not found",
                        status=404,
                        mimetype='text/plain')
    return resp


if __name__ == '__main__':
    DEBUG = os.environ.get('DEBUG', False)
    APP.run(host='0.0.0.0', debug=DEBUG)
