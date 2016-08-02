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
import operator
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

class CharmStoreObject(object):
    def __init__(self, url=None, path=None):
        self.series = None
        self.revision = None
        self.filename = None
        if url:
            logging.debug('parsing url {}'.format(url))
            result = re.search('^((cs:~[^/]+)/|(cs:))((.+)/)?(.+?)(-([0-9]+))?$', url)
            if result is None:
                raise CharmUrlParsingError("Cannot parse Charm url {}. Is this a local charm url? Only charmstore urls are allowed. Use cs:~{} namespace for our charms.".format(url, USERNAME))
            self.namespace = result.group(2) if result.group(2) else result.group(3)
            self.name = result.group(6)
            self.revision = result.group(8)
            if '/bundle/' in url:
                self.type = 'bundle'
                self.filename = 'bundle.yaml'
            else:
                self.type = 'charm'
                self.series = result.group(5)
            assert url == self.url
        elif path:
            self.type = 'bundle'
            path = os.path.realpath(path)
            if path.endswith('.yaml'):
                self.filename = os.path.basename(path)
                path = os.path.dirname(path)
            else:
                self.filename = 'bundle.yaml'
            self.namespace = 'cs:~{}'.format(USERNAME)
            self.name = os.path.basename(path)
            self._path = path
            assert self.dirpath == path
        else:
            assert False
        logging.debug('charm is {}'.format(self))

    def create_url(self, include_revision=True):
        logging.debug('creating charmstore url for {}'.format(self))
        url = self.namespace
        if not url.endswith(':'):
            url += "/"
        if self.type == 'bundle':
            url += "bundle/"
        if self.series:
            url += "{}/".format(self.series)
        url += self.name
        if include_revision and self.revision:
            url += '-{}'.format(self.revision)
        logging.debug('url is {}'.format(url))
        return url

    def push(self):
        """ pushes the local charm/bundle to the charmers personal namespace, channel 'unpublished', and grants everyone acces to the channel."""
        logging.debug("pushing {}".format(self.dirpath))
        output = subprocess.check_output(['charm', 'push', self.dirpath], universal_newlines=True)
        url = yaml.safe_load(output)['url']
        self.revision = url.split('-')[-1]
        url_without_revision = self.create_url(include_revision=False)
        subprocess.check_call(['charm', 'grant', url_without_revision, 'everyone', '--channel', 'unpublished'])

    def publish(self, channel):
        """publishes the charm/bundle to the specified channel of the charmers personal namespace"""
        if self.name == "init-bundle": # TODO: remove this fix
            return
        url = self.create_url()
        url_without_revision = self.create_url(include_revision=False)
        logging.debug("publishing {}".format(url))
        subprocess.check_call(['charm', 'publish', url, '--channel', channel])
        subprocess.check_call(['charm', 'grant', url_without_revision, 'everyone', '--channel', channel])

    @property
    def url(self):
        return self.create_url()

    @property
    def dirpath(self):
        if self.type == 'charm':
            return os.path.realpath('{}/{}/{}'.format(JUJU_REPOSITORY, self.series, self.name))
        if self.type == 'bundle':
            return self._path
        assert False

    @property
    def filepath(self):
        if self.type == 'bundle':
            return '{}/{}'.format(self.dirpath, self.filename)
        assert False # Charms don't have a specific file





def replace_charm_urls(filepath, charms):
    logging.debug('replacing {} in '.format(filepath))
    replacers = generate_replacers(charms)
    with open(filepath, 'r+') as stream:
        bundle = yaml.safe_load(stream)
        for (key, value) in bundle['services'].items():
            charmname = CharmStoreObject(value['charm']).name
            candidate = replacers.get(charmname)
            if candidate:
                bundle['services'][key]['charm'] = candidate
        stream.seek(0)
        stream.write(yaml.dump(bundle))
        stream.truncate()

def generate_replacers(charms):
    replacers = dict()
    for charm in charms:
        replacers[charm.name] = charm.url
    return replacers

def get_charms_from_bundle(bundle, namespace_whitelist=None):
    """ returns a set of paths to all charms in bundle that are owned by the user from `charm whoami`."""
    charms = []
    with open(bundle.filepath, 'r+') as stream:
        bundle = yaml.safe_load(stream)
    for value in bundle['services'].values():
        charm = CharmStoreObject(value['charm'])
        if namespace_whitelist is None or charm.namespace in namespace_whitelist:
            charms.append(charm)
    return charms

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

def bootstrap_testdir(sojobo_bundle, remote_bundle, init_bundle, charms_to_test):
    tmpdir = tempfile.mkdtemp()
    os.mkdir("{}/remote/".format(tmpdir))
    shutil.copytree(sojobo_bundle.dirpath, "{}/{}".format(tmpdir, sojobo_bundle.name))
    shutil.copytree(remote_bundle.dirpath, "{}/remote/{}".format(tmpdir, remote_bundle.name))
    shutil.copy(init_bundle.filepath, "{}/remote/init-bundle.yaml".format(tmpdir))

    with open('testplan.yaml', 'r') as stream:
        testplan = yaml.safe_load(stream.read())
    testplan['bundle'] = sojobo_bundle.name
    with open('{}/testplan.yaml'.format(tmpdir), 'w') as stream:
        stream.write(yaml.dump(testplan))
        testplan['bundle'] = sojobo_bundle.name

    testplan['bundle'] = remote_bundle.name
    with open('{}/remote/testplan.yaml'.format(tmpdir), 'w') as stream:
        stream.write(yaml.dump(testplan))

    replace_charm_urls("{}/{}/bundle.yaml".format(tmpdir, sojobo_bundle.name), charms_to_test)
    replace_charm_urls("{}/remote/{}/bundle.yaml".format(tmpdir, remote_bundle.name), charms_to_test)
    replace_charm_urls("{}/remote/init-bundle.yaml".format(tmpdir), charms_to_test)

    with open("{}/remote/init-bundle.yaml".format(tmpdir), 'rb') as stream:
        init_bundle = stream.read()

    with open("{}/{}/bundle.yaml".format(tmpdir, sojobo_bundle.name), 'r+') as stream:
        bundle = yaml.safe_load(stream)
        bundle['services']['hauchiwa'].setdefault('options', dict())['init-bundle'] = base64.b64encode(init_bundle).decode("utf-8")
        bundle['services']["h-{}".format(remote_bundle.name)] = bundle['services'].pop('hauchiwa')
        for relation in bundle['relations']:
            for endidx, endpoint in enumerate(relation):
                relation[endidx] = endpoint.replace('hauchiwa:', "h-{}:".format(remote_bundle.name))
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
    try:
        subprocess.check_call(["cat latest-sojobo.json | grep -q '\"test_outcome\": \"All Passed\"'"], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))
    except subprocess.CalledProcessError:
        return False
    return True

def run_tests(testdir, resultdir, sleeptime):
    with open('{}/remote/testplan.yaml'.format(testdir), 'r') as stream:
        bundle_name = os.path.basename(yaml.safe_load(stream)['bundle'])
        h_name = "h-{}".format(bundle_name)
    unit_n = subprocess.check_output(["juju status --format oneline | grep {} | cut -d '/' -f 2 | cut -d ':' -f 1".format(h_name)], shell=True, universal_newlines=True).rstrip()

    api_hostport = subprocess.check_output(['juju status --format tabular | grep {}/ | egrep -o ">22 [^-]+" | sed "s/^>22 //"'.format(h_name)], shell=True, universal_newlines=True).rstrip()

    from time import sleep

    sleep(sleeptime)

    with open('{}/remote/{}/bundle.yaml'.format(testdir, bundle_name), 'r') as bundle_file:
        bundle = bundle_file.read()
    response = requests.put('http://{}/{}/'.format(api_hostport, h_name[2:12]), data=bundle, headers={'Accept': 'application/json'})
    logging.info('request to http://{}, answer status code is {}, content is {}'.format(api_hostport, response.status_code, response.text))
    if response.status_code != 200:
        return False
    subprocess.check_call(['juju', 'scp', '--', '-r', '{}/remote/.'.format(testdir), '{}/{}:~/remote'.format(h_name, unit_n)]) #/remote/. : trailing dot is to make cp idempotent:  https://unix.stackexchange.com/questions/228597/how-to-copy-a-folder-recursively-in-an-idempotent-way-using-cp
    subprocess.check_call(
        ['juju', 'ssh', '{}/{}'.format(h_name, unit_n), '-Ct',
         "cd remote; cwr --no-destroy {0} testplan.yaml --no-destroy -l DEBUG --result-output {0}".format(bundle_name[:10])])
    logging.info('SCP')
    subprocess.check_call(['juju', 'scp', '--', '-r', '{}/{}:~/remote/results/.'.format(h_name, unit_n), '{}/remote/results'.format(testdir)])
    mergecopytree('{}/remote/results'.format(testdir), '{}/{}/'.format(resultdir, bundle_name))
    subprocess.check_call(['ln -sf `ls -v | grep result.html | tail -1` latest.html'], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))
    subprocess.check_call(['ln -sf `ls -v | grep result.json | tail -1` latest.json'], shell=True, cwd='{}/{}/'.format(resultdir, bundle_name))
    try:
        subprocess.check_call(["cat latest.json | grep -q '\"test_outcome\": \"All Passed\"'"], shell=True, cwd='{}/remote/results'.format(testdir))
    except subprocess.CalledProcessError:
        return False
    return True

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


def test_bundles(bundles_to_test, resultdir, reset):
    if reset == 'FULL' or reset == 'MODEL':
        for bundle in bundles_to_test:
            h_name = "h-{}".format(bundle.name)
            unit_n = subprocess.check_output(["juju status --format oneline | grep {} | cut -d '/' -f 2 | cut -d ':' -f 1".format(h_name)], shell=True, universal_newlines=True).rstrip()
            if unit_n:
                subprocess.check_call(
                    ['juju', 'ssh', '{}/{}'.format(h_name, unit_n), '-Ct',
                     "if [[ $(juju switch --list) ]]; then echo y | tengu destroy {0}; fi".format(bundle.name[:10])])
    if reset == 'FULL':
        subprocess.check_call(['echo y | tengu reset tenguci'], shell=True)
    logging.info("testing bundles at \n\t{}\nWriting results to {}".format("\n\t".join([b.dirpath for b in bundles_to_test]), resultdir))
    # Get all charms that have to be pushed
    sojobo_bundle = CharmStoreObject(path='{}/../bundles/sojobo/bundle.yaml'.format(JUJU_REPOSITORY))
    init_bundle = CharmStoreObject(path='{}/trusty/hauchiwa/files/tengu_management/templates/init-bundle.yaml'.format(JUJU_REPOSITORY))
    charms_to_test = []
    # charms in hauchiwa and init bundle need to be pushed but those bundles don't need to be tested
    for bundle in bundles_to_test + [sojobo_bundle, init_bundle]:
        charms_to_test = charms_to_test + get_charms_from_bundle(bundle, namespace_whitelist=["cs:~" + USERNAME])
    charms_to_test = list({v.url:v for v in charms_to_test}.values())

    # Push all charms that will be tested
    logging.info("Pushing the following charms to 'staging': \n\t{}\n".format("\n\t".join([c.url for c in charms_to_test])))
    for charm in charms_to_test:
        charm.push()
    logging.info("Pushing the following bundles to 'staging': \n\t{}\n".format("\n\t".join([c.url for c in bundles_to_test])))
    for bundle in bundles_to_test:
        bundle.push()
    logging.info("Pushed Charms: \n\t{}\n".format("\n\t".join([c.url for c in charms_to_test])))

    # Setup the directory for each bundle
    testdirs = []
    for bundle in bundles_to_test:
        testdirs.append(bootstrap_testdir(sojobo_bundle, bundle, init_bundle, charms_to_test))




    # First hauchiwa can't be created in parallell because bundledeployer might try to deploy
    # rest2jfed while it already exists. (race condition because they ask for permission instead of forgiveness)
    create_hauchiwa(testdirs[0], resultdir)

    with Pool(5) as pool:
        result = pool.starmap(create_hauchiwa, [[testdir, resultdir] for testdir in testdirs[1:]])
    # Due to a bug, the pool will hang if one of the run_tests functions exits, so we do it here.
    if False in result:
        exit(1)

    sleeptime = 0

    # Run tests (run_tests should throw exception if test fails)
    # This runs in parallell
    logging.info("Running tests in: \n\t{}\n".format("\n\t".join(testdirs)))
    with Pool(5) as pool:
        result = pool.starmap(run_tests, [[testdir, resultdir, operator.iadd(sleeptime, 20)] for testdir in testdirs])
    # Due to a bug, the pool will hang if one of the run_tests functions exits, so we do it here.
    if False in result:
        exit(1)

    # If all tests succeed, publish all charms
    logging.info("Publishing charms/bundles: \n\t{}\n".format("\n\t".join([c.url for c in charms_to_test + bundles_to_test])))
    for csobject in charms_to_test + bundles_to_test:
        csobject.publish('stable')


@click.group()
def g_cli():
    pass


@click.command(name='test')
@click.argument(
    'bundles', type=click.Path(exists=True), nargs=-1)
@click.argument(
    'resultdir', nargs=1)
@click.option(
    '--reset',
    default='FULL',
    help="How to reset the system. FULL = destroy model and hauchiwa, MODEL = destroy model, NONE = don't reset anything")
def c_test(bundles, resultdir, reset):
    """ test given bundles """
    test_bundles([CharmStoreObject(path=bundle) for bundle in bundles], resultdir, reset)


g_cli.add_command(c_test)


if __name__ == '__main__':
    g_cli()
