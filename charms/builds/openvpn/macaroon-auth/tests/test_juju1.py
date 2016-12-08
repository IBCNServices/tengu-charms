import copy
import errno
import mock
import os
import pytest
import shutil
import socket
import ssl
import tempfile
import unittest
import yaml

import jujuclient
import jujuclient.utils

from jujuclient.juju1.connector import Connector
from jujuclient.juju1.environment import Environment
from jujuclient.juju1.rpc import RPC
from jujuclient.juju1.watch import WaitForNoMachines
from jujuclient.juju1.facades import (
    Actions,
    Annotations,
    Backups,
    Charms,
    HA,
    KeyManager,
    UserManager,
)

from jujuclient.exc import (
    EnvError,
    EnvironmentNotBootstrapped,
)
from jujuclient.connector import SSL_VERSION

# skip this entire test module unless we're running on juju 1.x
pytestmark = pytest.mark.skipif(
    jujuclient.utils.get_juju_major_version() != 1,
    reason="Running Juju 1.x tests only",
)

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python doesn't verify by default (see pep-0476)
    #   https://www.python.org/dev/peps/pep-0476/
    pass


ENV_NAME = os.environ.get("JUJU_TEST_ENV")

if not ENV_NAME:
    raise ValueError("No Testing Environment Defined.")

SAMPLE_CONFIG = {
    'user': 'tester',
    'password': 'sekrit',
    'environ-uuid': 'some-uuid',
    'server-uuid': 'server-uuid',
    'state-servers': ['localhost:12345'],
    'ca-cert': 'test-cert',
}


def reset(env):
    status = env.status()
    for s in status['Services'].keys():
        env.destroy_service(s)
    if env.version == 0:
        env.destroy_machines(sorted(status['Machines'].keys())[1:], force=True)
    else:
        env.destroy_machines(sorted(status['Machines'].keys()), force=True)
    watch = env.get_watch()
    WaitForNoMachines(watch, status['Machines']).run()
    while True:
        status = env.status()
        if len(status['Services']) == 0:
            break


class ClientRPCTest(unittest.TestCase):

    @mock.patch('jujuclient.juju1.rpc.RPC._send_request')
    @mock.patch('jujuclient.juju1.rpc.RPC._upgrade_retry_delay_secs', 0.001)
    def test_retry_on_upgrade_error(self, send_request):
        send_request.return_value = {"Error": "upgrade in progress"}
        rpc_client = RPC()
        rpc_client.conn = mock.Mock()
        self.assertRaises(EnvError, rpc_client.login, "password")
        self.assertEquals(send_request.call_count, 61)

    @mock.patch('jujuclient.juju1.rpc.RPC._send_request')
    def test_no_retry_required(self, send_request):
        send_request.return_value = {"Error": "some other error"}
        rpc_client = RPC()
        rpc_client.conn = mock.Mock()
        self.assertRaises(EnvError, rpc_client.login, "password")
        self.assertEquals(send_request.call_count, 1)


class ClientConnectorTest(unittest.TestCase):

    def mkdir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        return d

    @mock.patch('jujuclient.connector.websocket')
    def test_connect_socket(self, websocket):
        address = "wss://abc:17070"
        Connector.connect_socket(address)
        websocket.create_connection.assert_called_once_with(
            address, origin=address, sslopt={
                'ssl_version': SSL_VERSION,
                'cert_reqs': ssl.CERT_NONE})

    @mock.patch('socket.create_connection')
    def test_is_server_available_unknown_error(self, connect_socket):
        connect_socket.side_effect = ValueError()
        self.assertRaises(
            ValueError, Connector().is_server_available,
            'foo.example.com:7070')

    @mock.patch('socket.create_connection')
    def test_is_server_available_known_error(self, connect_socket):
        e = socket.error()
        e.errno = errno.ETIMEDOUT
        connect_socket.side_effect = e
        self.assertFalse(
            Connector().is_server_available("foo.example.com:7070"))

    def test_split_host_port_dns(self):
        self.assertEqual(
            Connector.split_host_port('foo.example.com:7070'),
            ('foo.example.com', '7070')
        )

    def test_is_server_available_ipv4(self):
        self.assertEqual(
            Connector.split_host_port('10.0.0.10:7070'),
            ('10.0.0.10', '7070')
        )

    def test_is_server_available_ipv6(self):
        self.assertEqual(
            Connector.split_host_port('[2001:db8::1]:7070'),
            ('2001:db8::1', '7070')
        )

    def test_is_server_available_invalid_input(self):
        self.assertRaises(
            ValueError, Connector.split_host_port, 'I am not an ip/port combo'
        )

    def test_parse_env_missing(self):
        temp_juju_home = self.mkdir()
        with mock.patch.dict('os.environ', {'JUJU_HOME': temp_juju_home}):
            connector = Connector()
            self.assertRaises(
                EnvironmentNotBootstrapped,
                connector.parse_env,
                'missing')

    def test_parse_env_jenv(self):
        temp_juju_home = self.mkdir()
        self.write_jenv(temp_juju_home, 'test-model', SAMPLE_CONFIG)
        with mock.patch.dict('os.environ', {'JUJU_HOME': temp_juju_home}):
            connector = Connector()
            home, env = connector.parse_env('test-model')
            self.assertEqual(home, temp_juju_home)
            self.assertEqual(env, SAMPLE_CONFIG)

    def test_parse_cache_file(self):
        temp_juju_home = self.mkdir()
        self.write_cache_file(temp_juju_home, 'test-model', SAMPLE_CONFIG)
        with mock.patch.dict('os.environ', {'JUJU_HOME': temp_juju_home}):
            connector = Connector()
            home, env = connector.parse_env('test-model')
            self.assertEqual(home, temp_juju_home)
            self.assertEqual(env, SAMPLE_CONFIG)

    def test_parse_cache_file_missing_env(self):
        """Create a valid cache file, but look for an environment that isn't
        there.
        """
        temp_juju_home = self.mkdir()
        self.write_cache_file(temp_juju_home, 'test-model', SAMPLE_CONFIG)
        with mock.patch.dict('os.environ', {'JUJU_HOME': temp_juju_home}):
            connector = Connector()
            self.assertRaises(
                EnvironmentNotBootstrapped,
                connector.parse_env,
                'missing')

    def test_parse_env_cache_file_first(self):
        """The cache file has priority over a jenv file."""
        temp_juju_home = self.mkdir()
        content = copy.deepcopy(SAMPLE_CONFIG)
        self.write_jenv(temp_juju_home, 'test-model', content)
        # Now change the password.
        content['password'] = 'new password'
        self.write_cache_file(temp_juju_home, 'test-model', content)
        with mock.patch.dict('os.environ', {'JUJU_HOME': temp_juju_home}):
            connector = Connector()
            home, env = connector.parse_env('test-model')
            self.assertEqual(home, temp_juju_home)
            self.assertEqual(env, content)

    def write_jenv(self, juju_home, env_name, content):
        env_dir = os.path.join(juju_home, 'environments')
        if not os.path.exists(env_dir):
            os.mkdir(env_dir)
        jenv = os.path.join(env_dir, '%s.jenv' % env_name)
        with open(jenv, 'w') as f:
            yaml.dump(content, f, default_flow_style=False)

    def write_cache_file(self, juju_home, env_name, content):
        env_dir = os.path.join(juju_home, 'environments')
        if not os.path.exists(env_dir):
            os.mkdir(env_dir)
        filename = os.path.join(env_dir, 'cache.yaml')
        cache_content = {
            'environment': {
                env_name: {'env-uuid': content['environ-uuid'],
                           'server-uuid': content['server-uuid'],
                           'user': content['user']}},
            'server-data': {
                content['server-uuid']: {
                    'api-endpoints': content['state-servers'],
                    'ca-cert': content['ca-cert'],
                    'identities': {content['user']: content['password']}}},
            # Explicitly don't care about 'server-user' here.
            }
        with open(filename, 'w') as f:
            yaml.dump(cache_content, f, default_flow_style=False)


class KeyManagerTest(unittest.TestCase):
    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.keys = KeyManager(self.env)

    def tearDown(self):
        self.env.close()

    def verify_keys(self, expected, user='admin', present=True):
        keys = self.keys(user)['Results'][0]['Result']
        for e in expected:
            found = False
            for k in keys:
                if e in k:
                    found = True
                    break
            if not present:
                if found:
                    raise AssertionError("%s not found in %s" % (e, keys))
                return
            if not found:
                raise AssertionError("%s not found in %s" % (e, keys))

    @pytest.mark.skipif(True, reason="not implemented")
    def test_key_manager(self):
        self.verify_keys(['juju-client-key', 'juju-system-key'])
        self.assertEqual(
            self.key.import_keys('admin', ['hazmat']),
            {u'Results': [{u'Error': None}]})
        self.verify_keys(['ssh-import-id lp:hazmat'])
        self.key.delete(
            'admin',
            'kapil@objectrealms-laptop.local # ssh-import-id lp:hazmat')
        self.verify_keys(['ssh-import-id lp:hazmat'], present=False)


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.bm = Backups(self.env)

    def tearDown(self):
        self.env.close()

    @pytest.mark.skipif(True, reason="broken cleanup")
    def test_backups(self):
        assert self.bm.list()['List'] == []
        info = self.bm.create('abc')
        assert len(self.bm.list()['List']) == 2
        assert self.bm.info(info['ID'])['Notes'] == 'abc'
        self.bm.remove(info['ID'])
        assert len(self.bm.list()['List']) == []


class UserManagerTest(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.um = UserManager(self.env)

    def tearDown(self):
        self.env.close()

    def assert_user(self, user):
        result = self.um.info(user['username'])
        result = result['results'][0]['result']
        result.pop('date-created')
        self.assertEqual(result, user)

    @pytest.mark.skipif(True, reason="broken cleanup")
    def test_user_manager(self):
        result = self.um.add(
            {'username': 'magicmike', 'display-name': 'zerocool',
             'password': 'guess'})
        assert result == {'results': [{'tag': 'user-magicmike@local'}]}
        self.assert_user({
            'username': 'magicmike',
            'disabled': False,
            'display-name': 'zerocool',
            'created-by': 'admin@local'})
        self.um.disable('mike')
        self.assert_user({
            'username': 'magicmike',
            'disabled': True,
            'display-name': 'zerocool',
            'created-by': 'admin@local'})
        self.um.enable('mike')
        self.assert_user({
            'username': 'magicmike',
            'disabled': False,
            'display-name': 'zerocool',
            'created-by': 'admin@local'})
        self.assertEqual(
            self.um.set_password({'username': 'mike', 'password': 'iforgot'}),
            {u'Results': [{u'Error': None}]})
        self.um.disable('mike')


class CharmBase(object):

    _repo_dir = None

    @property
    def repo_dir(self):
        if not self._repo_dir:
            self._repo_dir = self.mkdir()
        return self._repo_dir

    def mkdir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        return d

    def write_local_charm(self, md, config=None, actions=None):
        charm_dir = os.path.join(self.repo_dir, md['series'], md['name'])
        if not os.path.exists(charm_dir):
            os.makedirs(charm_dir)
        md_path = os.path.join(charm_dir, 'metadata.yaml')
        with open(md_path, 'w') as fh:
            md.pop('series', None)
            fh.write(yaml.safe_dump(md))

        if config is not None:
            cfg_path = os.path.join(charm_dir, 'config.yaml')
            with open(cfg_path, 'w') as fh:
                fh.write(yaml.safe_dump(config))

        if actions is not None:
            act_path = os.path.join(charm_dir, 'actions.yaml')
            with open(act_path, 'w') as fh:
                fh.write(yaml.safe_dump(actions))

        with open(os.path.join(charm_dir, 'revision'), 'w') as fh:
            fh.write('1')


class ActionTest(unittest.TestCase, CharmBase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.actions = Actions(self.env)
        self.setupCharm()

    def tearDown(self):
        self.env.close()

    def setupCharm(self):
        actions = {
            'deepsix': {
                'description': 'does something with six',
                'params': {
                    'optiona': {
                        'type': 'string',
                        'default': 'xyz'}}}}
        self.write_local_charm({
            'name': 'mysql',
            'summary': 'its a db',
            'description': 'for storing things',
            'series': 'trusty',
            'provides': {
                'db': {
                    'interface': 'mysql'}}}, actions=actions)

    @pytest.mark.skipif(True, reason="broken test call to api")
    def test_actions(self):
        result = self.env.add_local_charm_dir(
            os.path.join(self.repo_dir, 'trusty', 'mysql'),
            'trusty')
        charm_url = result['CharmURL']
        self.env.deploy('action-db', charm_url)
        actions = self.actions.service_actions('action-db')
        self.assertEqual(
            actions,
            {u'results': [
                {u'servicetag': u'service-action-db',
                 u'actions': {u'ActionSpecs':
                              {u'deepsix': {
                                  u'Params': {u'title': u'deepsix',
                                              u'type': u'object',
                                              u'description':
                                              u'does something with six',
                                              u'properties': {
                                                  u'optiona': {
                                                      u'default': u'xyz',
                                                      u'type': u'string'}}},
                                  u'Description': u'does something with six'
                              }}}}]})
        result = self.actions.enqueue_units(
            'action-db/0', 'deepsix', {'optiona': 'bez'})
        self.assertEqual(result, [])


class CharmTest(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.charms = Charms(self.env)

    def tearDown(self):
        self.env.close()

    def test_charm(self):
        self.charms.list()
        self.env.add_charm('cs:~hazmat/trusty/etcd-6')
        self.charms.list()
        self.charms.info('cs:~hazmat/trusty/etcd-6')


class HATest(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.ha = HA(self.env)

    def tearDown(self):
        self.env.close()

    @pytest.mark.skipif(True, reason="incomplete implementation issue")
    def test_ha(self):
        previous = self.env.status()
        self.ha.ensure_availability(3)
        current = self.env.status()
        self.assertNotEqual(previous, current)


class AnnotationTest(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)
        self.charms = Annotations(self.env)

    def tearDown(self):
        self.env.close()


class ClientTest(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)

    def tearDown(self):
        reset(self.env)
        self.env = None

    def destroy_service(self, svc):
        self.env.destroy_service(svc)
        while True:
            if svc not in self.env.status().get('Services', {}):
                break

    def assert_service(self, svc_name, num_units=None):
        status = self.env.status()
        services = status.get('Services', {})
        self.assertTrue(
            svc_name in services,
            "Service {} does not exist".format(svc_name)
        )
        if num_units is not None:
            count = len(services[svc_name]['Units'])
            self.assertTrue(
                count == num_units,
                "Service {} has {} units, expected {}".format(
                    svc_name, count, num_units)
            )

    def assert_not_service(self, svc_name):
        status = self.env.status()
        services = status.get('Services', {})
        if svc_name in services:
            self.assertTrue(
                services[svc_name]['Life'] in ('dying', 'dead'))

    def test_juju_info(self):
        info_keys = list(sorted(self.env.info().keys()))
        control = [
            'DefaultSeries', 'Name', 'ProviderType', 'ServerUUID', 'UUID']
        assert info_keys == control

    def test_add_get_charm(self):
        self.env.add_charm('cs:~hazmat/trusty/etcd-6')
        charm = self.env.get_charm(
            'cs:~hazmat/trusty/etcd-6')
        assert charm['URL'] == 'cs:~hazmat/trusty/etcd-6'

    def test_add_local_charm(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertRaises(
                EnvError, self.env.add_local_charm, f.name, 'trusty')

    def test_deploy_and_destroy(self):
        self.assert_not_service('db')
        self.env.deploy('db', 'cs:trusty/mysql-1')
        self.assert_service('db')
        self.destroy_service('db')
        self.assert_not_service('db')

    def xtest_expose_unexpose(self):
        pass

    def test_add_remove_units(self):
        self.assert_not_service('db')
        machine_1 = self.env.add_machine(series="trusty")['Machine']
        machine_2 = self.env.add_machine(series="trusty")['Machine']
        self.env.deploy('db', 'cs:trusty/mysql-1', machine_spec=machine_1)
        self.env.add_unit('db', machine_spec=machine_2)
        self.assert_service('db', num_units=2)
        services = self.env.status().get('Services', {})
        # Remove the first unit
        remove_unit = list(services['db']['Units'].keys())[0]
        self.env.remove_units([remove_unit])
        self.assert_service('db', num_units=1)
        self.destroy_service('db')
        self.assert_not_service('db')

    def test_deploy_and_add_unit_lxc(self):
        self.assert_not_service('db')
        machine = self.env.add_machine(series="trusty")['Machine']
        self.env.deploy('db', 'cs:trusty/mysql-1', machine_spec=machine)
        self.env.add_unit('db', machine_spec='lxc:{}'.format(machine))
        self.assert_service('db', num_units=2)
        self.destroy_service('db')
        self.assert_not_service('db')

    def xtest_get_set_config(self):
        pass

    def test_get_set_constraints(self):
        self.assert_not_service('db')
        in_constraints = {'cpu-cores': '2'}
        self.env.deploy('db', 'cs:trusty/mysql-1', constraints=in_constraints)
        self.assert_service('db')
        out_constraints = self.env.get_constraints('db')
        self.assertEqual(in_constraints, out_constraints)
        self.destroy_service('db')
        self.assert_not_service('db')

    def test_get_set_annotations(self):
        machine = self.env.add_machine(series="trusty")['Machine']
        in_annotation = {'foo': 'bar'}
        self.env.set_annotation(machine, 'machine', in_annotation)
        out_annotation = self.env.get_annotation(machine, 'machine')
        self.assertEqual(in_annotation, out_annotation['Annotations'])

    def xtest_add_remove_relation(self):
        pass

    def xtest_status(self):
        pass

    def xtest_info(self):
        pass

    def test_deploy_and_destroy_placement_machine(self):
        self.assert_not_service('db')
        machine = self.env.add_machine(series="trusty")['Machine']
        self.env.deploy('db', 'cs:trusty/mysql-1', machine_spec=machine)
        self.assert_service('db')
        self.destroy_service('db')
        self.assert_not_service('db')

    def test_deploy_and_destroy_placement_lxc(self):
        self.assert_not_service('db')
        machine = self.env.add_machine(series="trusty")['Machine']
        machine_spec = 'lxc:{}'.format(machine)
        self.env.deploy('db', 'cs:trusty/mysql-1', machine_spec=machine_spec)
        self.assert_service('db')
        self.destroy_service('db')
        self.assert_not_service('db')


class TestEnvironment(unittest.TestCase):

    def setUp(self):
        self.env = Environment.connect(ENV_NAME)

    def test_make_headers(self):
        headers = self.env._make_headers()
        self.assertTrue('Authorization' in headers)

    def test_run_no_target(self):
        self.assertRaises(AssertionError, self.env.run, "sudo test")

    def test_run_target_machines(self):
        with mock.patch.object(self.env, '_rpc',
                               return_value=None) as rpc:
            self.env.run("sudo test", machines=["0", "1"])

            rpc.assert_called_once_with({
                "Type": "Client",
                "Version": 0,
                "Request": "Run",
                "Params": {
                    "Commands": "sudo test",
                    "Timeout": None,
                    "Machines": [
                        '0',
                        '1',
                    ]
                }
            })

    def test_run_target_services(self):
        with mock.patch.object(self.env, '_rpc',
                               return_value=None) as rpc:
            self.env.run("sudo test", services=["cinder", "glance"])

            rpc.assert_called_once_with({
                "Type": "Client",
                "Version": 0,
                "Request": "Run",
                "Params": {
                    "Commands": "sudo test",
                    "Timeout": None,
                    "Services": [
                        'cinder',
                        'glance',
                    ]
                }
            })

    def test_run_target_units(self):
        with mock.patch.object(self.env, '_rpc',
                               return_value=None) as rpc:
            self.env.run("sudo test", units=["mysql/0", "mysql/1"])

            rpc.assert_called_once_with({
                "Type": "Client",
                "Version": 0,
                "Request": "Run",
                "Params": {
                    "Commands": "sudo test",
                    "Timeout": None,
                    "Units": [
                        'mysql/0',
                        'mysql/1',
                    ]
                }
            })


if __name__ == '__main__':
    unittest.main()
