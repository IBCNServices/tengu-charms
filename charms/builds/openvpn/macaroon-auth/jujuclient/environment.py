from base64 import b64encode
import json
import os
import shutil
import stat
import tempfile
import urllib
import warnings
import zipfile

import websocket

from .exc import EnvError

# py 2 and py 3 compat
try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection


class BaseEnvironment(object):
    """A client to a juju environment."""

    def __init__(self, endpoint, name=None, conn=None,
                 ca_cert=None, env_uuid=None):
        self.name = name
        self.endpoint = endpoint
        self._watches = []

        # For watches.
        self._creds = None
        self._ca_cert = ca_cert
        self._info = None
        self._env_uuid = env_uuid

        if conn is not None:
            self.conn = conn
        else:
            self.conn = self.connector().connect_socket(
                endpoint, self._ca_cert)

    @classmethod
    def connector(cls):
        raise NotImplementedError()

    @classmethod
    def watch_module(cls):
        raise NotImplementedError()

    @classmethod
    def facade_class(cls):
        raise NotImplementedError()

    @property
    def tag(self):
        raise NotImplementedError()

    @property
    def juju_home(self):
        raise NotImplementedError()

    @property
    def url_root(self):
        raise NotImplementedError()

    def get_facades(self):
        raise NotImplementedError()

    def get_facade_name(self, facade_dict):
        raise NotImplementedError()

    def get_facade_versions(self, facade_dict):
        raise NotImplementedError()

    def close(self):
        """Close the connection and any extant associated watches."""
        for w in self._watches:
            w.stop()
        if self.conn.connected:
            self.conn.close()

    @classmethod
    def connect(cls, env_name):
        """Connect and login to the named environment."""
        connector = cls.connector()
        return connector().run(cls, env_name)

    @property
    def uuid(self):
        return self._env_uuid

    def login(self, password, user="user-admin"):
        """Login to the environment.
        """
        result = super(BaseEnvironment, self).login(
            password, user)
        self.negotiate_facades()
        return result

    def _make_headers(self):
        return {
            'Authorization': 'Basic %s' % b64encode(
                (u'%(user)s:%(password)s' % (self._creds)).encode()).decode()
        }

    def _http_conn(self):
        endpoint = self.endpoint.replace('wss://', '')
        host, remainder = endpoint.split(':', 1)
        port = remainder
        if '/' in remainder:
            port, _ = remainder.split('/', 1)
        conn = HTTPSConnection(host, int(port))
        path = ""
        if self.uuid:
            path = "{}/{}".format(self.url_root, self.uuid)
        return conn, self._make_headers(), path

    # Charm ops / see charm facade for listing charms in environ.
    def add_local_charm_dir(self, charm_dir, series):
        """Add a local charm to the environment.

        This will automatically generate an archive from
        the charm dir and then add_local_charm.
        """
        fh = tempfile.NamedTemporaryFile()
        CharmArchiveGenerator(charm_dir).make_archive(fh.name)
        with fh:
            return self.add_local_charm(
                fh, series, os.stat(fh.name).st_size)

    def add_local_charm(self, charm_file, series, size=None):
        """Add a local charm to an environment.

        Uses an https endpoint at the same host:port as the wss.
        Supports large file uploads.
        """
        conn, headers, path_prefix = self._http_conn()
        path = "%s/charms?series=%s" % (path_prefix, series)
        headers['Content-Type'] = 'application/zip'
        # Specify if its a psuedo-file object,
        # httplib will try to stat non strings.
        if size:
            headers['Content-Length'] = size
        conn.request("POST", path, charm_file, headers)
        response = conn.getresponse()
        result = json.loads(response.read().decode())
        if not response.status == 200:
            raise EnvError(result)
        return result

    def download_charm(self, charm_url, path=None, fh=None):
        """Download a charm from the env to the given path or file like object.

        Returns the integer size of the downloaded file::

          >>> env.add_charm('cs:~hazmat/trusty/etcd-6')
          >>> env.download_charm('cs:~hazmat/trusty/etcd-6', 'etcd.zip')
          3649263
        """
        if not path and not fh:
            raise ValueError("Must provide either path or fh")
        conn, headers, path_prefix = self._http_conn()
        url_path = "%s/charms?file=*&url=%s" % (path_prefix, charm_url)
        if path:
            fh = open(path, 'wb')
        with fh:
            conn.request("GET", url_path, "", headers)
            response = conn.getresponse()
            if response.status != 200:
                raise EnvError({"Error": response.read()})
            shutil.copyfileobj(response, fh, 2 ** 15)
            size = fh.tell()
        return size

    def get_charm(self, charm_url):
        """Get information about a charm in the environment.

        Example::

          >>> env.get_charm('cs:~hazmat/trusty/etcd-6')

         {u'URL': u'cs:~hazmat/trusty/etcd-6',
            u'Meta': {
                u'Peers': {
                    u'cluster': {u'Name': u'cluster', u'Limit': 1, u'Scope':
                    u'global', u'Interface': u'etcd-raft', u'Role': u'peer',
                    u'Optional': False}},
                u'OldRevision': 0,
                u'Description': u"...",
                u'Format': 1, u'Series': u'', u'Tags': None, u'Storage': None,
                u'Summary': u'A distributed key value store for configuration',
                u'Provides': {u'client': {
                    u'Name':u'client', u'Limit': 0, u'Scope': u'global',
                    u'Interface':u'etcd', u'Role': u'provider',
                    u'Optional': False}},
                u'Subordinate': False, u'Requires': None, u'Categories': None,
                u'Name': u'etcd'},
                u'Config': {u'Options': {
                    u'debug': {
                        u'Default': True, u'Type': u'boolean',
                        u'Description': u'Enable debug logging'},
              u'snapshot': {u'Default': True, u'Type': u'boolean',
              u'Description': u'Enable log snapshots'}}},
           u'Actions': {u'ActionSpecs': None},
           u'Revision': 6}
        """
        return self._rpc(
            {"Type": "Client",
             "Request": "CharmInfo",
             "Params": {
                 "CharmURL": charm_url}})

    def debug_log(self, include_entity=(), include_module=(),
                  exclude_entity=(), exclude_module=(), limit=0,
                  back_log=0, level=None, replay=False):
        """Return an iterator over juju logs in the environment.

        >>> logs = env.debug_log(back_log=10, limit=20)
        >>> for l in logs: print l
        """
        d = {}
        if include_entity:
            d['includeEntity'] = include_entity
        if include_module:
            d['includeModule'] = include_module
        if exclude_entity:
            d['excludeEntity'] = exclude_entity
        if exclude_module:
            d['excludeModule'] = exclude_module
        if limit:
            d['maxLines'] = limit
        if level:
            d['level'] = level
        if back_log:
            d['backlog'] = back_log
        if replay:
            d['replay'] = str(bool(replay)).lower()

        # ca cert for ssl cert validation if present.
        cert_pem = os.path.join(
            os.path.expanduser(self.juju_home),
            'jclient',
            "%s.pem" % self.name)
        if not os.path.exists(cert_pem):
            cert_pem = None
        sslopt = self.connector().get_ssl_config(cert_pem)

        p = urllib.urlencode(d)
        if self._env_uuid:
            url = self.endpoint.rsplit('/', 1)[0]
            url += "/log"
        else:
            url = self.endpoint + "/log"

        if p:
            url = "%s?%s" % (url, p)

        conn = websocket.create_connection(
            url, origin=self.endpoint, sslopt=sslopt,
            header=self._make_headers())

        # Error message if any is pre-pended.
        result = json.loads(conn.recv())
        if 'Error' in result or 'error' in result:
            conn.close()
            raise EnvError(result)

        return LogIterator(conn)

    # Watch Wrapper methods
    def get_stat(self):
        """DEPRECATED: A status emulator using the watch api, returns
        immediately.

        """
        warnings.warn(
            "get_stat is deprecated, use status()", DeprecationWarning)
        return self.status()

    def wait_for_units(
            self, timeout=None, goal_state="started", callback=None):
        """Wait for all units to reach a given state.

        Any unit errors will cause an exception to be raised.

        """
        watch = self.get_watch(timeout)
        return self.watch_module().WaitForUnits(
            watch, goal_state).run(callback)

    def wait_for_no_machines(self, timeout, callback=None):
        """For unit tests doing teardowns, or deployer during reset.

        """
        watch = self.get_watch(timeout)
        return self.watch_module().WaitForNoMachines(watch).run(callback)

    def get_watch(self, timeout=None, connection=None, watch_class=None):
        """Get a watch connection to observe changes to the environment.

        """
        # Separate conn per watcher to keep sync usage simple, else we have to
        # buffer watch results with requestid dispatch. At the moment
        # with the all watcher, an app only needs one watch, which is likely to
        # change to discrete watches on individual bits.
        if connection is None:
            watch_env = self.__class__(self.endpoint)
            watch_env.login(**self._creds)
            if self._debug:
                watch_env._debug = True
        else:
            watch_env = connection

        p = dict(self._creds)
        p.update({
            'url': self.endpoint,
            'origin': self.endpoint,
            'ca_cert': self._ca_cert})
        if timeout is not None:
            if watch_class is None:
                watch_class = self.watch_module().TimeoutWatcher
            watcher = watch_class(watch_env.conn)
            watcher.set_timeout(timeout)
        else:
            if watch_class is None:
                watch_class = self.watch_module().Watcher
            watcher = watch_class(watch_env.conn)
        watcher.set_reconnect_params(p)
        self._watches.append(watcher)
        watcher.start()
        return watcher

    watch = get_watch

    def negotiate_facades(self):
        """Auto-negotiate api facades available based on server login information.

        This annotates facades instances directly onto env/client as well as
        a 'facades' mapping of facade name to version & attribute.

        """
        def subclasses(cls):
            """Recursively get all subclasses of ``cls``"""
            for i in cls.__subclasses__():
                for j in subclasses(i):
                    yield j
                yield i

        def get_facade_class(versions, facade_classes):
            """Return a facade class that matches a list of versions"""
            # Check for latest versions first
            for v in sorted(versions, reverse=True):
                for cls in facade_classes:
                    if v in cls.versions:
                        return cls, v
            return None, None

        facade_map = {}
        for factory in subclasses(self.facade_class()):
            facade_map.setdefault(factory.name, []).append(factory)

        facades = {}
        for fenv in self.get_facades() or []:
            facade_classes = facade_map.get(self.get_facade_name(fenv), [])
            facade_class, version = get_facade_class(
                self.get_facade_versions(fenv), facade_classes)
            if not facade_class:
                continue

            f = facade_class(self, version)
            setattr(self, f.key, f)
            facades[f.name] = {'attr': f.key, 'version': version}
        setattr(self, 'facades', facades)

    def add_relation(self, *args, **kws):
        return self.service.add_relation(*args, **kws)

    def remove_relation(self, *args, **kws):
        return self.service.remove_relation(*args, **kws)

    def deploy(self, *args, **kws):
        return self.service.deploy(*args, **kws)

    def set_config(self, *args, **kws):
        return self.service.set_config(*args, **kws)

    def unset_config(self, *args, **kws):
        return self.service.unset_config(*args, **kws)

    def set_charm(self, *args, **kws):
        return self.service.set_charm(*args, **kws)

    def get_service(self, *args, **kws):
        return self.service.get_service(*args, **kws)

    def get_config(self, *args, **kws):
        return self.service.get_config(*args, **kws)

    def get_constraints(self, *args, **kws):
        return self.service.get_constraints(*args, **kws)

    def set_constraints(self, *args, **kws):
        return self.service.set_constraints(*args, **kws)

    def update_service(self, *args, **kws):
        return self.service.update_service(*args, **kws)

    def destroy_service(self, *args, **kws):
        return self.service.destroy_service(*args, **kws)

    def expose(self, *args, **kws):
        return self.service.expose(*args, **kws)

    def unexpose(self, *args, **kws):
        return self.service.unexpose(*args, **kws)

    def valid_relation_names(self, *args, **kws):
        return self.service.valid_relation_names(*args, **kws)

    def add_units(self, *args, **kws):
        return self.service.add_units(*args, **kws)

    def add_unit(self, *args, **kws):
        return self.service.add_unit(*args, **kws)

    def remove_units(self, *args, **kws):
        return self.service.remove_units(*args, **kws)

    def get_annotation(self, *args, **kws):
        return self.client.get_annotation(*args, **kws)

    def set_annotation(self, *args, **kws):
        return self.client.set_annotation(*args, **kws)

    def resolved(self, *args, **kws):
        return self.client.resolved(*args, **kws)

    def get_public_address(self, *args, **kws):
        return self.client.get_public_address(*args, **kws)

    def get_private_address(self, *args, **kws):
        return self.client.get_private_address(*args, **kws)

    def add_charm(self, *args, **kws):
        return self.client.add_charm(*args, **kws)

    def resolve_charms(self, *args, **kws):
        return self.client.resolve_charms(*args, **kws)

    def retry_provisioning(self, *args, **kws):
        return self.client.retry_provisioning(*args, **kws)

    def machine_config(self, *args, **kws):
        return self.client.machine_config(*args, **kws)

    def provisioning_script(self, *args, **kws):
        return self.client.provisioning_script(*args, **kws)

    def destroy_machines(self, *args, **kws):
        return self.client.destroy_machines(*args, **kws)

    def register_machines(self, *args, **kws):
        return self.client.register_machines(*args, **kws)

    def register_machine(self, *args, **kws):
        return self.client.register_machine(*args, **kws)

    def add_machines(self, *args, **kws):
        return self.client.add_machines(*args, **kws)

    def add_machine(self, *args, **kws):
        return self.client.add_machine(*args, **kws)

    def run(self, *args, **kws):
        return self.client.run(*args, **kws)

    def run_on_all_machines(self, *args, **kws):
        return self.client.run_on_all_machines(*args, **kws)

    def find_tools(self, *args, **kws):
        return self.client.find_tools(*args, **kws)

    def agent_version(self, *args, **kws):
        return self.client.agent_version(*args, **kws)

    def set_agent_env_version(self, *args, **kws):
        return self.client.set_agent_env_version(*args, **kws)

    def unset_env_config(self, *args, **kws):
        return self.client.unset_env_config(*args, **kws)

    def set_env_config(self, *args, **kws):
        return self.client.set_env_config(*args, **kws)

    def get_env_config(self, *args, **kws):
        return self.client.get_env_config(*args, **kws)

    def set_env_constraints(self, *args, **kws):
        return self.client.set_env_constraints(*args, **kws)

    def get_env_constraints(self, *args, **kws):
        return self.client.get_env_constraints(*args, **kws)

    def status(self, *args, **kws):
        return self.client.status(*args, **kws)

    def info(self, *args, **kws):
        return self.client.info(*args, **kws)


class CharmArchiveGenerator(object):

    def __init__(self, path):
        self.path = path

    def make_archive(self, path):
        """Create archive of directory and write to ``path``.
        :param path: Path to archive
        Ignored
        - build/* - This is used for packing the charm itself and any
                    similar tasks.
        - */.*    - Hidden files are all ignored for now.  This will most
                    likely be changed into a specific ignore list (.bzr, etc)
        """
        zf = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(self.path):
            relative_path = dirpath[len(self.path) + 1:]
            if relative_path and not self._ignore(relative_path):
                zf.write(dirpath, relative_path)
            for name in filenames:
                archive_name = os.path.join(relative_path, name)
                if not self._ignore(archive_name):
                    real_path = os.path.join(dirpath, name)
                    self._check_type(real_path)
                    if os.path.islink(real_path):
                        self._check_link(real_path)
                        self._write_symlink(
                            zf, os.readlink(real_path), archive_name)
                    else:
                        zf.write(real_path, archive_name)
        zf.close()
        return path

    def _check_type(self, path):
        """Check the path
        """
        s = os.stat(path)
        if stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode):
            return path
        raise ValueError("Invalid Charm at % %s" % (
            path, "Invalid file type for a charm"))

    def _check_link(self, path):
        link_path = os.readlink(path)
        if link_path[0] == "/":
            raise ValueError(
                "Invalid Charm at %s: %s" % (
                    path, "Absolute links are invalid"))
        path_dir = os.path.dirname(path)
        link_path = os.path.join(path_dir, link_path)
        if not link_path.startswith(os.path.abspath(self.path)):
            raise ValueError(
                "Invalid charm at %s %s" % (
                    path, "Only internal symlinks are allowed"))

    def _write_symlink(self, zf, link_target, link_path):
        """Package symlinks with appropriate zipfile metadata."""
        info = zipfile.ZipInfo()
        info.filename = link_path
        info.create_system = 3
        # Magic code for symlinks / py2/3 compat
        # 27166663808 = (stat.S_IFLNK | 0755) << 16
        info.external_attr = 2716663808
        zf.writestr(info, link_target)

    def _ignore(self, path):
        if path == "build" or path.startswith("build/"):
            return True
        if path.startswith('.'):
            return True


class Jobs(object):
    HostUnits = "JobHostUnits"
    ManageEnviron = "JobManageEnviron"
    ManageState = "JobManageState"


class LogIterator(object):

    def __init__(self, conn):
        self.conn = conn

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.conn.recv()
        except websocket.WebSocketConnectionClosedException:
            self.conn.close()
            raise StopIteration()
        except Exception:
            self.conn.close()
            raise

    __next__ = next
