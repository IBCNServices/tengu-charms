#!/usr/bin/env python
""" REST server that calls the jfed_cli tool """
from flask import Flask, Response, request
import tempfile
import base64
import os
import json
# Custom modules
from jfed_utils import JFed # pylint: disable=F0401

APP = Flask(__name__)


PROPERTIES_PATH = '/opt/jfedS4/context_tengujfed_wall2.properties'
LIB_LOCATION = '/opt/jfedS4'
JAVA_PATH = '/opt/java/jre1.8.0_45/bin/java'
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
                None,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    output = jfed.get_userinfo()
    resp = Response(output,
                    status=200,
                    mimetype='text/plain')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>', methods=['POST'])
def api_slice_put(projectname, slicename):
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
    jfed = JFed(rspec_path,
                projectname,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    # Check if slice already exists, make folder if it doesn't exist
    if not os.path.isdir(slice_dir):
        if os.path.isfile(manifest_path) and jfed.exp_exists(slicename):
            resp = Response("Cannot modify existing slice",
                            status=409,
                            mimetype='text/plain')
            return resp
        else:
            os.makedirs(slice_dir)
    # Run command
    status = jfed.create_slice(slicename, manifest_path)

    # Return rspec or error
    if status == 'SUCCESS':
        with open(manifest_path, 'r') as manifest_f:
            resp = Response(manifest_f.read(),
                            status=201,
                            mimetype='application/xml')
            resp.headers['Link'] = 'slice/%s' % slicename
    else:
        resp = Response("slice creation failed with status {0}".format(status),
                        status=500,
                        mimetype='text/plain')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>', methods=['DELETE'])
def api_slice_delete(projectname, slicename):
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
    jfed = JFed(manifest_path,
                projectname,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    output = jfed.delete_slice(slicename)
    resp = Response("slice deleted sucessfully. Output:" + output,
                    status=200,
                    mimetype='text/plain')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/status', methods=['GET'])
def api_sliver_status(projectname, slicename):
    """ Returns the status of the slice """
    # Get post values
    cert = request.headers.get('emulab-s4-cert')
    extended = json.loads(request.args.get('extended', default='false'))
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
    jfed = JFed(manifest_path,
                projectname,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    # Run command
    status = jfed.sliver_status(slicename, extended=extended)
    # Return response or error
    if status:
        resp = Response(status,
                        status=200,
                        mimetype='text/plain')
    else:
        resp = Response("Getting status failed.",
                        status=500,
                        mimetype='text/plain')
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
    jfed = JFed(None,
                projectname,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    output = jfed.get_sliceinfo(slicename)
    resp = Response(output,
                    status=200,
                    mimetype='text/plain')
    return resp


@APP.route('/projects/<projectname>/slices/<slicename>/expiration',
           methods=['POST'])
def api_slice_expiration(projectname, slicename):
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
    jfed = JFed(manifest_path,
                projectname,
                LIB_LOCATION,
                s4cert=cert_path,
                properties=PROPERTIES_PATH,
                java_path=JAVA_PATH)
    # Run command
    output = jfed.renew_slice(slicename, exp_hours)
    # Return response or error
    if 'This is not your credential' in output:
        resp = Response(output,
                        status=403,
                        mimetype='text/plain')
    elif 'does not exist. Cannot continue.' in output:
        resp = Response(output,
                        status=404,
                        mimetype='text/plain')
    elif 'has been renewed successfully' in output:
        resp = Response("Slice renewed: "+ output,
                        status=200,
                        mimetype='text/plain')
    else:
        resp = Response("Slice renewing failed: "+ output,
                        status=500,
                        mimetype='text/plain')
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
    APP.run(host='0.0.0.0')
