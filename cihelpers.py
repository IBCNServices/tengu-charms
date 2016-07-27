#!/usr/bin/python3
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
# pylint: disable=c0111,c0301,w1202
import re
import os
import errno
import shutil
import base64
import logging
import tempfile
import subprocess
from multiprocessing import Pool

import click
import yaml
import requests

JUJU_REPOSITORY = os.environ.get('JUJU_REPOSITORY', '.')
FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level='INFO', format=FORMAT)


def get_username():
    output = subprocess.check_call(['charm', 'login'], universal_newlines=True)
    output = subprocess.check_output(['charm', 'whoami'], universal_newlines=True)
    return yaml.safe_load(output)['User']

USERNAME = get_username()

class CharmUrlParsingError(Exception):
    pass

def replace_charm_url(filename, charms):
    logging.debug('replacing {} in '.format(filename))
    replacers = generate_replacers(charms)
    with open(filename, 'r+') as stream:
        bundle = yaml.safe_load(stream)
        for (key, value) in bundle['services'].items():
            charmname = parse_charm_url(value['charm'])['name']
            candidate = replacers.get(charmname)
            if candidate:
                bundle['services'][key]['charm'] = candidate
        stream.seek(0)
        stream.write(yaml.dump(bundle))
        stream.truncate()

def generate_replacers(charms):
    replacers = dict()
    for charm in charms:
        replacers[charm['name']] = charm['url']
    return replacers

def parse_charm_url(url):
    logging.debug('parsing url {}'.format(url))
    result = re.search('^((cs:~[^/]+)/|(cs:))((.+)/)?(.+?)(-([0-9]+))?$', url)
    if result is None:
        raise CharmUrlParsingError("Cannot parse Charm url {}. Is this a local charm url? Only charmstore urls are allowed. Use CS:~{} namespace for our charms.".format(url, USERNAME))
    charm = {
        'namespace': result.group(2) if result.group(2) else result.group(3),
        'series': result.group(4),
        'name': result.group(6),
        'revision': result.group(8),
        'url': url,
    }
    logging.debug('charm is {}'.format(charm))
    return charm

def create_charm_url(charm, include_revision=True):
    logging.debug('creating charm url for {}'.format(charm))
    url = charm['namespace']
    if not url.endswith(':'):
        url += "/"
    if charm.get('series'):
        url += "{}/".format(charm['series'])
    url += charm['name']
    if include_revision and charm.get('revision'):
        url += '-{}'.format(charm['revision'])
    logging.debug('url is {}'.format(url))
    return url

def get_charms_from_bundle(bundle_path, namespace_whitelist=None):
    """ returns a set of paths to all charms in bundle that are owned by the user from `charm whoami`."""
    charms = []
    with open(bundle_path, 'r+') as stream:
        bundle = yaml.safe_load(stream)
    for value in bundle['services'].values():
        charm = parse_charm_url(value['charm'])
        if namespace_whitelist is None or charm['namespace'] in namespace_whitelist:
            charms.append(charm)
    return charms

def push_charm(charm):
    """ pushes the local charm to the charmers personal namespace, channel 'unpublished', and grants everyone acces to the channel."""
    charm_path = '{}/../charms/{}/{}'.format(JUJU_REPOSITORY, charm['series'], charm['name'])
    logging.debug("pushing {}".format(charm_path))
    output = subprocess.check_output(['charm', 'push', charm_path], universal_newlines=True)
    url = yaml.safe_load(output)['url']
    charm = parse_charm_url(url)
    url_without_revision = create_charm_url(charm, include_revision=False)
    subprocess.check_call(['charm', 'grant', url_without_revision, 'everyone', '--channel', 'unpublished'])
    return charm

def publish_charm(charm):
    """ published the charm to the specified channel of the charmers personal namespace"""
    charm_url = create_charm_url(charm)
    url_without_revision = create_charm_url(charm, include_revision=False)
    logging.debug("publishing {}".format(charm_url))
    subprocess.check_call(['charm', 'publish', charm_url, '--channel', charm['channel']])
    subprocess.check_call(['charm', 'grant', url_without_revision, 'everyone', '--channel', charm['channel']])

def mergecopytree(src, dst, symlinks=False, ignore=None):
    """"Recursive copy src to dst, mergecopy directory if dst exists.
    OVERWRITES EXISTING FILES!!"""
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if symlinks and os.path.islink(src_item):
            if os.path.lexists(dst_item):
                os.remove(dst_item)
            os.symlink(os.readlink(src_item), dst_item)
        elif os.path.isdir(src_item):
            mergecopytree(src_item, dst_item, symlinks, ignore)
        else:
            shutil.copy2(src_item, dst_item)

def bootstrap_testdir(local_bundle_path, remote_bundle_path, init_bundle_path, charms_to_test):
    local_bundle_dir = os.path.dirname(local_bundle_path).rstrip('/')
    remote_bundle_dir = os.path.dirname(remote_bundle_path).rstrip('/')
    local_bundle_name = os.path.basename(local_bundle_dir)
    remote_bundle_name = os.path.basename(remote_bundle_dir)
    tmpdir = tempfile.mkdtemp()
    os.mkdir("{}/remote/".format(tmpdir))
    shutil.copytree(local_bundle_dir, "{}/{}".format(tmpdir, local_bundle_name))
    shutil.copytree(remote_bundle_dir, "{}/remote/{}".format(tmpdir, remote_bundle_name))
    shutil.copy(init_bundle_path, "{}/remote/init-bundle.yaml".format(tmpdir))

    with open('testplan.yaml', 'r') as stream:
        testplan = yaml.safe_load(stream.read())
    testplan['bundle'] = local_bundle_name
    with open('{}/testplan.yaml'.format(tmpdir), 'w') as stream:
        stream.write(yaml.dump(testplan))
        testplan['bundle'] = local_bundle_name

    testplan['bundle'] = remote_bundle_name
    with open('{}/remote/testplan.yaml'.format(tmpdir), 'w') as stream:
        stream.write(yaml.dump(testplan))

    replace_charm_url("{}/{}/bundle.yaml".format(tmpdir, local_bundle_name), charms_to_test)
    replace_charm_url("{}/remote/{}/bundle.yaml".format(tmpdir, remote_bundle_name), charms_to_test)
    replace_charm_url("{}/remote/init-bundle.yaml".format(tmpdir), charms_to_test)

    with open("{}/remote/init-bundle.yaml".format(tmpdir), 'rb') as stream:
        init_bundle = stream.read()

    with open("{}/{}/bundle.yaml".format(tmpdir, local_bundle_name), 'r+') as stream:
        bundle = yaml.safe_load(stream)
        bundle['services']['hauchiwa'].setdefault('options', dict())['init-bundle'] = base64.b64encode(init_bundle).decode("utf-8")
        bundle['services']["h-{}".format(remote_bundle_name)] = bundle['services'].pop('hauchiwa')
        for relation in bundle['relations']:
            for endidx, endpoint in enumerate(relation):
                relation[endidx] = endpoint.replace('hauchiwa:', "h-{}:".format(remote_bundle_name))
        stream.seek(0)
        stream.write(yaml.dump(bundle))
    return tmpdir

def create_hauchiwa(testdir, resultdir):
    with open('{}/remote/testplan.yaml'.format(testdir), 'r') as stream:
        bundle_name = os.path.basename(yaml.safe_load(stream)['bundle'])
        h_name = "h-{}".format(bundle_name)
    try:
        os.makedirs('{}/{}/'.format(resultdir, bundle_name))
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    subprocess.check_call(['cwr', '--no-destroy', 'tenguci', 'testplan.yaml', '--no-destroy', '-l', 'DEBUG', '-o', '{}/{}/'.format(resultdir, bundle_name), '--result-output', '{}'.format(h_name)], cwd='{}'.format(testdir))

    subprocess.check_call(['ln -sf `ls -v | egrep "sojobo.+result\\.html" | tail -1` latest-sojobo.html'], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))
    subprocess.check_call(['ln -sf `ls -v | egrep "sojobo.+result\\.json" | tail -1` latest-sojobo.json'], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))
    subprocess.check_call(["cat latest-sojobo.json | grep -q '\"test_outcome\": \"All Passed\"'"], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))

def run_tests(testdir, resultdir):
    with open('{}/remote/testplan.yaml'.format(testdir), 'r') as stream:
        bundle_name = os.path.basename(yaml.safe_load(stream)['bundle'])
        h_name = "h-{}".format(bundle_name)
    unit_n = subprocess.check_output(["juju status --format oneline | grep {} | cut -d '/' -f 2 | cut -d ':' -f 1".format(h_name)], shell=True, universal_newlines=True).rstrip()

    api_hostport = subprocess.check_output(['juju status --format tabular | grep {}/ | egrep -o ">22 [^-]+" | sed "s/^>22 //"'.format(h_name)], shell=True, universal_newlines=True).rstrip()

    with open('{}/remote/{}/bundle.yaml'.format(testdir, bundle_name), 'r') as bundle_file:
        bundle = bundle_file.read()
    response = requests.put('http://{}/{}/'.format(api_hostport, h_name[2:12]), data=bundle, headers={'Accept': 'application/json'})
    logging.info('request to http://{}, answer status code is {}, content is {}'.format(api_hostport, response.status_code, response.text))
    subprocess.check_call(['juju', 'scp', '--', '-r', '{}/remote/.'.format(testdir), '{}/{}:~/remote'.format(h_name, unit_n)]) #/remote/. : trailing dot is to make cp idempotent:  https://unix.stackexchange.com/questions/228597/how-to-copy-a-folder-recursively-in-an-idempotent-way-using-cp
    subprocess.check_call(
        ['juju', 'ssh', '{}/{}'.format(h_name, unit_n), '-C',
         "cd remote; cwr --no-destroy {0} testplan.yaml --no-destroy -l DEBUG --result-output {0}".format(bundle_name[:10])])
    logging.info('SCP')
    subprocess.check_call(['juju', 'scp', '--', '-r', '{}/{}:~/remote/results/.'.format(h_name, unit_n), '{}/remote/results'.format(testdir)])
    subprocess.check_call(['ln -sf `ls -v | grep result.html | tail -1` latest.html'], shell=True, cwd='{}/remote/results'.format(testdir))
    subprocess.check_call(['ln -sf `ls -v | grep result.json | tail -1` latest.json'], shell=True, cwd='{}/remote/results'.format(testdir))
    mergecopytree('{}/remote/results'.format(testdir), '{}/{}/'.format(resultdir, bundle_name))
    logging.info('DESTROY ENVIRONMENT')
    subprocess.check_call(
        ['juju', 'ssh', '{}/{}'.format(h_name, unit_n), '-C',
         "echo y | tengu destroy {0}".format(bundle_name[:10])])
    subprocess.check_call(["cat latest.json | grep -q '\"test_outcome\": \"All Passed\"'"], shell=True, cwd='{}/remote/results'.format(testdir))

def get_changed():
    GIT_PREVIOUS_SUCCESSFUL_COMMIT = os.environ.get('GIT_PREVIOUS_SUCCESSFUL_COMMIT') # pylint:disable=c0103
    changed = {
        'ci': False,
        'charms': [],
        'bundles': [],
    }
    output = subprocess.check_output(['git', 'diff', GIT_PREVIOUS_SUCCESSFUL_COMMIT, '--name-only'], universal_newlines=True)
    for line in output.split('\n'):
        if ['ci.sh', 'cihelpers.py', 'cihelpers.py'] in line:
            changed['ci'] = True
        result = re.search('/bundles/([^/])/', line)
        if result:
            changed['charms'].append(result.group(0))
            return
        result = re.search('/charms/[^/]/([^/])', line)
        if result:
            changed['bundles'].append(result.group(0))
            return


def test_bundles(bundles_to_test, resultdir):
    subprocess.check_call(['/usr/bin/tengu', 'reset', 'tenguci'])
    logging.info("testing bundles at \n\t{}\nWriting results to {}".format("\n\t".join(bundles_to_test), resultdir))
    # Get all charms that have to be pushed
    sojobo_bundle = '{}/../bundles/sojobo/bundle.yaml'.format(JUJU_REPOSITORY)
    init_bundle = '{}/../charms/trusty/hauchiwa/files/tengu_management/templates/init-bundle.yaml'.format(JUJU_REPOSITORY)
    charms_to_push = []
    # charms in hauchiwa and init bundle need to be pushed but those bundles don't need to be tested
    for bundle in bundles_to_test + (sojobo_bundle, init_bundle):
        charms_to_push = charms_to_push + get_charms_from_bundle(bundle, namespace_whitelist=["cs:~" + USERNAME])
    charms_to_push = list({v['url']:v for v in charms_to_push}.values())

    # Push all charms that will be tested
    logging.info("Pushing the following charms to 'staging': \n\t{}\n".format("\n\t".join([c['url'] for c in charms_to_push])))
    charms_to_test = []
    for charm in charms_to_push:
        charms_to_test.append(push_charm(charm))
    logging.info("Pushed Charms: \n\t{}\n".format("\n\t".join([c['url'] for c in charms_to_test])))

    # Setup the directory for each bundle
    testdirs = []
    for bundle in bundles_to_test:
        testdirs.append(bootstrap_testdir(sojobo_bundle, bundle, init_bundle, charms_to_test))

    # Create the hauchiwas for running the tests. Running this in paralell doesn't seem to work...
    for testdir in testdirs:
        create_hauchiwa(testdir, resultdir)


    # Run tests (run_tests should throw exception if test fails)
    # This runs in parallell
    logging.info("Running tests in: \n\t{}\n".format("\n\t".join(testdirs)))
    with Pool(5) as pool:
        pool.starmap(run_tests, [[testdir, resultdir] for testdir in testdirs])


    # If all tests succeed, publish all charms
    logging.info("Publishing charms: \n\t{}\n".format("\n\t".join([c['url'] for c in charms_to_test])))
    for charm in charms_to_test:
        charm['channel'] = 'stable'
        publish_charm(charm)


@click.group()
def g_cli():
    pass


@click.command(name='test')
@click.argument(
    'bundles', nargs=-1)
@click.argument(
    'resultdir', nargs=1)
def c_test(bundles, resultdir):
    """ publish given charm urls to revision """
    test_bundles(bundles, resultdir)


g_cli.add_command(c_test)


if __name__ == '__main__':
    g_cli()
