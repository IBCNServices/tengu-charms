# Copyright 2014-2015 Canonical Limited.
#
# This file is part of jujubigdata.
#
# jujubigdata is free software: you can redistribute it and/or modify
# it under the terms of the Apache License version 2.0.
#
# jujubigdata is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.

import pwd
import json

from charmhelpers.core import hookenv
from charmhelpers.core.charmframework.helpers import Relation, any_ready_unit

from jujubigdata import utils


class SpecMatchingRelation(Relation):
    """
    Relation base class that validates that a version and environment
    between two related charms match, to prevent interoperability issues.

    This class adds a ``spec`` key to the ``required_keys`` and populates it
    in :meth:`provide`.  The ``spec`` value must be passed in to :meth:`__init__`.

    The ``spec`` should be a mapping (or a callback that returns a mapping)
    which describes all aspects of the charm's environment or configuration
    that might affect its interoperability with the remote charm.  The charm
    on the requires side of the relation will verify that all of the keys in
    its ``spec`` are present and exactly equal on the provides side of the
    relation.  This does mean that the requires side can be a subset of the
    provides side, but not the other way around.

    An example spec string might be::

        {
            'arch': 'x86_64',
            'vendor': 'apache',
            'version': '2.4',
        }
    """
    def __init__(self, spec=None, *args, **kwargs):
        """
        Create a new relation handler instance.

        :param str spec: Spec string that should capture version or environment
            particulars which can cause issues if mismatched.
        """
        super(SpecMatchingRelation, self).__init__(*args, **kwargs)
        self._spec = spec

    @property
    def spec(self):
        if callable(self._spec):
            return self._spec()
        return self._spec

    def provide(self, remote_service, all_ready):
        """
        Provide the ``spec`` data to the remote service.

        Subclasses *must* either delegate to this method (e.g., via `super()`)
        or include ``'spec': json.dumps(self.spec)`` in the provided data themselves.
        """
        data = super(SpecMatchingRelation, self).provide(remote_service, all_ready)
        if self.spec:
            data['spec'] = json.dumps(self.spec)
        return data

    def filtered_data(self, remote_service=None):
        if self.spec and 'spec' not in self.required_keys:
            self.required_keys.append('spec')
        return super(SpecMatchingRelation, self).filtered_data(remote_service)

    def is_ready(self):
        """
        Validate the ``spec`` data from the connected units to ensure that
        it matches the local ``spec``.
        """
        if not super(SpecMatchingRelation, self).is_ready():
            return False
        if not self.spec:
            return True
        for unit, data in self.filtered_data().items():
            remote_spec = json.loads(data.get('spec', '{}'))
            for k, v in self.spec.items():
                if v != remote_spec.get(k):
                    # TODO XXX Once extended status reporting is available,
                    #          we should use that instead of erroring.
                    raise ValueError(
                        'Spec mismatch with related unit %s: '
                        '%r != %r' % (unit, data.get('spec'), json.dumps(self.spec)))
        return True


class SSHRelation(Relation):
    ssh_user = 'ubuntu'

    def __init__(self, *args, **kwargs):
        super(SSHRelation, self).__init__(*args, **kwargs)
        if 'ssh-key' not in self.required_keys:
            self.required_keys = self.required_keys + ['ssh-key']

    def install_ssh_keys(self):
        unit, data = any_ready_unit(self.relation_name)
        ssh_key = data['ssh-key']
        utils.install_ssh_key(self.ssh_user, ssh_key)

    def provide(self, remote_service, all_ready):
        data = super(SSHRelation, self).provide(remote_service, all_ready)
        try:
            pwd.getpwnam(self.ssh_user)
        except KeyError:
            hookenv.log('Cannot provide SSH key yet, user not available: %s' % self.ssh_user)
        else:
            data.update({
                'ssh-key': utils.get_ssh_key(self.ssh_user),
            })
        return data


class EtcHostsRelation(Relation):
    def __init__(self, *args, **kwargs):
        super(EtcHostsRelation, self).__init__(*args, **kwargs)
        if 'etc_hosts' not in self.required_keys:
            self.required_keys = self.required_keys + ['etc_hosts']

    def provide(self, remote_service, all_ready):
        data = super(EtcHostsRelation, self).provide(remote_service, all_ready)
        data.update({
            'etc_hosts': json.dumps(utils.get_kv_hosts()),
        })
        return data

    def register_connected_hosts(self):
        for unit, data in self.unfiltered_data().items():
            ip = utils.resolve_private_address(data['private-address'])
            name = unit.replace('/', '-')
            utils.update_kv_host(ip, name)

    def register_provided_hosts(self):
        unit, data = any_ready_unit(self.relation_name)
        provided_hosts = json.loads(data['etc_hosts'])
        hookenv.log('Registering hosts from %s: %s' % (unit, provided_hosts))
        for ip, name in provided_hosts.items():
            utils.update_kv_host(ip, name)

    def am_i_registered(self):
        my_ip = utils.resolve_private_address(hookenv.unit_get('private-address'))
        my_hostname = hookenv.local_unit().replace('/', '-')
        unit, data = any_ready_unit(self.relation_name)
        etc_hosts = json.loads((data or {}).get('etc_hosts', '{}'))
        return etc_hosts.get(my_ip, None) == my_hostname


class NameNode(SpecMatchingRelation, EtcHostsRelation):
    """
    Relation which communicates the NameNode (HDFS) connection & status info.

    This is the relation that clients should use.
    """
    relation_name = 'namenode'
    required_keys = ['private-address', 'has_slave', 'port', 'webhdfs-port']
    require_slave = True

    def __init__(self, spec=None, port=None, webhdfs_port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        self.webhdfs_port = webhdfs_port  # only needed for provides
        utils.initialize_kv_host()
        super(NameNode, self).__init__(spec, *args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(NameNode, self).provide(remote_service, all_ready)
        if all_ready and utils.wait_for_jps('NameNode', 300):
            data.update({
                'has_slave': DataNode().is_ready(),
                'port': self.port,
                'webhdfs-port': self.webhdfs_port,
            })
        return data

    def has_slave(self):
        """
        Check if the NameNode has any DataNode slaves registered. This reflects
        if HDFS is ready without having to wait for utils.wait_for_hdfs.
        """
        if not super(NameNode, self).is_ready():
            return False
        data = self.filtered_data().values()[0]
        return utils.strtobool(data['has_slave'])

    def is_ready(self):
        _is_ready = super(NameNode, self).is_ready()
        if self.require_slave:
            return _is_ready and self.has_slave()
        else:
            return _is_ready


class NameNodeMaster(NameNode, SSHRelation):
    """
    Alternate NameNode relation for DataNodes.
    """
    relation_name = 'datanode'
    ssh_user = 'hdfs'
    require_slave = False


class ResourceManager(SpecMatchingRelation, EtcHostsRelation):
    """
    Relation which communicates the ResourceManager (YARN) connection & status info.

    This is the relation that clients should use.
    """
    relation_name = 'resourcemanager'
    required_keys = ['private-address', 'has_slave', 'historyserver-http',
                     'historyserver-ipc', 'port']
    require_slave = True

    def __init__(self, spec=None, port=None, historyserver_http=None,
                 historyserver_ipc=None, *args, **kwargs):
        self.port = port  # only needed for provides
        self.historyserver_http = historyserver_http  # only needed for provides
        self.historyserver_ipc = historyserver_ipc    # only needed for provides
        utils.initialize_kv_host()
        super(ResourceManager, self).__init__(spec, *args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(ResourceManager, self).provide(remote_service, all_ready)
        if all_ready and utils.wait_for_jps('ResourceManager', 300):
            data.update({
                'has_slave': NodeManager().is_ready(),
                'port': self.port,
                'historyserver-http': self.historyserver_http,
                'historyserver-ipc': self.historyserver_ipc,
            })
        return data

    def has_slave(self):
        """
        Check if the ResourceManager has any NodeManager slaves registered.
        """
        if not super(ResourceManager, self).is_ready():
            return False
        data = self.filtered_data().values()[0]
        return utils.strtobool(data['has_slave'])

    def is_ready(self):
        _is_ready = super(ResourceManager, self).is_ready()
        if self.require_slave:
            return _is_ready and self.has_slave()
        else:
            return _is_ready


class ResourceManagerMaster(ResourceManager, SSHRelation):
    """
    Alternate ResourceManager relation for NodeManagers.
    """
    relation_name = 'nodemanager'
    ssh_user = 'yarn'
    require_slave = False


class DataNode(SpecMatchingRelation):
    """
    Relation which communicates DataNode info back to NameNodes.
    """
    relation_name = 'datanode'
    required_keys = ['private-address', 'hostname']

    def provide(self, remote_service, all_ready):
        data = super(DataNode, self).provide(remote_service, all_ready)
        hostname = hookenv.local_unit().replace('/', '-')
        data.update({
            'hostname': hostname,
        })
        return data


class SecondaryNameNode(SpecMatchingRelation):
    """
    Relation which communicates SecondaryNameNode info back to NameNodes.
    """
    relation_name = 'secondary'
    required_keys = ['private-address', 'hostname', 'port']

    def __init__(self, spec=None, port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        super(SecondaryNameNode, self).__init__(spec, *args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(SecondaryNameNode, self).provide(remote_service, all_ready)
        hostname = hookenv.local_unit().replace('/', '-')
        data.update({
            'hostname': hostname,
            'port': self.port,
        })
        return data


class NodeManager(Relation):
    """
    Relation which communicates NodeManager info back to ResourceManagers.
    """
    relation_name = 'nodemanager'
    required_keys = ['private-address', 'hostname']

    def provide(self, remote_service, all_ready):
        data = super(NodeManager, self).provide(remote_service, all_ready)
        hostname = hookenv.local_unit().replace('/', '-')
        data.update({
            'hostname': hostname,
        })
        return data


class HadoopPlugin(Relation):
    """
    This helper class manages the ``hadoop-plugin`` interface, and
    is the recommended way of interacting with the endpoint via this
    interface.

    Charms using this interface will have a JRE installed, the Hadoop
    API Java libraries installed, the Hadoop configuration managed in
    ``/etc/hadoop/conf``, and the environment configured in ``/etc/environment``.
    The endpoint will ensure that the distribution, version, Java, etc. are all
    compatible to ensure a properly functioning Hadoop ecosystem.

    Charms using this interface can call :meth:`is_ready` (or :meth:`hdfs_is_ready`)
    to determine if this relation is ready to use.
    """
    relation_name = 'hadoop-plugin'
    required_keys = ['yarn-ready', 'hdfs-ready']
    '''
    These keys will be set on the relation once everything is installed,
    configured, connected, and ready to receive work.  They can be
    checked by calling :meth:`is_ready`, or manually via Juju's ``relation-get``.
    '''

    def __init__(self, hdfs_only=False, *args, **kwargs):
        if hdfs_only:
            self.required_keys = ['hdfs-ready']
        super(HadoopPlugin, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        """
        Used by the endpoint to provide the :attr:`required_keys`.
        """
        hdfs_ready = NameNode().is_ready()
        yarn_ready = ResourceManager().is_ready()
        if hdfs_ready:
            # make sure we can actually reach HDFS
            utils.wait_for_hdfs(300)  # will error if timeout
        return {
            'hdfs-ready': utils.normalize_strbool(hdfs_ready),
            'yarn-ready': utils.normalize_strbool(yarn_ready),
        }

    def is_ready(self):
        if not super(HadoopPlugin, self).is_ready():
            return False
        data = self.filtered_data().values()[0]
        hdfs_ready = utils.strtobool(data.get('hdfs-ready', 'False'))
        yarn_ready = utils.strtobool(data.get('yarn-ready', 'False'))
        if 'hdfs-ready' in self.required_keys and not hdfs_ready:
            return False
        if 'yarn-ready' in self.required_keys and not yarn_ready:
            return False
        return True

    def hdfs_is_ready(self):
        """
        Check if the Hadoop libraries and installed and configured and HDFS is
        connected and ready to handle work (at least one DataNode available).

        (This is a synonym for :meth:`is_ready`.)
        """
        return self.is_ready()


class HadoopREST(Relation):
    """
    This helper class manages the ``hadoop-rest`` interface, and
    is the recommended way of interacting with the endpoint via this
    interface.

    Charms using this interface are provided with the API endpoint
    information for the NameNode, ResourceManager, and JobHistoryServer.
    """
    relation_name = 'hadoop-rest'
    required_keys = ['namenode-host', 'hdfs-port', 'webhdfs-port',
                     'resourcemanager-host', 'resourcemanager-port',
                     'historyserver-host', 'historyserver-port']

    def provide(self, remote_service, all_ready):
        """
        Used by the endpoint to provide the :attr:`required_keys`.
        """
        if not all_ready:
            return {}
        _, namenode = any_ready_unit(NameNode.relation_name)
        _, resourcemanager = any_ready_unit(ResourceManager.relation_name)
        return {
            'namenode-host': namenode['private-address'],
            'hdfs-port': namenode['port'],
            'webhdfs-port': namenode['webhdfs-port'],
            'resourcemanager-host': resourcemanager['private-address'],
            'resourcemanager-port': resourcemanager['port'],
            'historyserver-host': resourcemanager['private-address'],
            'historyserver-port': resourcemanager['historyserver-port'],
        }

    def _get(self, *keys):
        if not self.is_ready():
            return None
        data = self.filtered_data().values()[0]
        if not keys:
            return None
        elif len(keys) == 1:
            return data[keys[0]]
        else:
            return [data[key] for key in keys]

    @property
    def namenode_host(self):
        'Property containing the NameNode host, or ``None`` if not available.'
        return self._get('namenode-host')

    @property
    def hdfs_port(self):
        'Property containing the HDFS port, or ``None`` if not available.'
        return self._get('hdfs-port')

    @property
    def webhdfs_port(self):
        'Property containing the WebHDFS port, or ``None`` if not available.'
        return self._get('webhdfs-port')

    @property
    def resourcemanager_host(self):
        'Property containing the ResourceManager host, or ``None`` if not available.'
        return self._get('resourcemanager-host')

    @property
    def resourcemanager_port(self):
        'Property containing the ResourceManager port, or ``None`` if not available.'
        return self._get('resourcemanager-port')

    @property
    def historyserver_host(self):
        'Property containing the HistoryServer host, or ``None`` if not available.'
        return self._get('historyserver-host')

    @property
    def historyserver_port(self):
        'Property containing the HistoryServer port, or ``None`` if not available.'
        return self._get('historyserver-port')

    @property
    def hdfs_uri(self):
        'Property containing the full HDFS URI, or ``None`` if not available.'
        host, port = self._get('namenode-host', 'hdfs-port')
        if host and port:
            return 'hdfs://{}:{}'.format(host, port)
        else:
            return None

    @property
    def webhdfs_uri(self):
        'Property containing the full WebHDFS URI, or ``None`` if not available.'
        host, port = self._get('namenode-host', 'webhdfs-port')
        if host and port:
            return 'http://{}:{}/webhdfs/v1'.format(host, port)
        else:
            return None

    @property
    def resourcemanager_uri(self):
        'Property containing the full ResourceManager API URI, or ``None`` if not available.'
        host, port = self._get('resourcemanager-host', 'resourcemanager-port')
        if host and port:
            return 'http://{}:{}'.format(host, port)
        else:
            return None

    @property
    def historyserver_uri(self):
        'Property containing the full JobHistoryServer API URI, or ``None`` if not available.'
        host, port = self._get('historyserver-host', 'historyserver-port')
        if host and port:
            return 'http://{}:{}'.format(host, port)
        else:
            return None


class MySQL(Relation):
    relation_name = 'db'
    required_keys = ['host', 'database', 'user', 'password']


class FlumeAgent(Relation):
    relation_name = 'flume-agent'
    required_keys = ['private-address', 'port']

    def __init__(self, port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        super(FlumeAgent, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(FlumeAgent, self).provide(remote_service, all_ready)
        flume_protocol = hookenv.config('protocol')
        if (flume_protocol not in ['avro']):
            hookenv.log('Invalid flume protocol {}'.format(flume_protocol), hookenv.ERROR)
            return data
        if all_ready:
            data.update({
                'port': self.port,
                'protocol': hookenv.config('protocol'),
            })
        return data


class HBase(SSHRelation):
    relation_name = 'hbase'
    required_keys = ['private-address', 'master-port', 'region-port', 'ssh-key']

    def __init__(self, master=None, region=None, *args, **kwargs):
        self.master_port = master  # only needed for provides
        self.region_port = region  # only needed for provides
        super(HBase, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(HBase, self).provide(remote_service, all_ready)
        if all_ready:
            data.update({
                'master-port': self.master_port,
                'region-port': self.region_port,
            })
        return data


class Hive(Relation):
    relation_name = 'hive'
    required_keys = ['private-address', 'port', 'ready']

    def __init__(self, port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        super(Hive, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(Hive, self).provide(remote_service, all_ready)
        if all_ready:
            data.update({
                'ready': 'true',
                'port': self.port,
            })
        return data


class Kafka(Relation):
    relation_name = 'kafka'
    required_keys = ['private-address', 'port']

    def __init__(self, port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        super(Kafka, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(Kafka, self).provide(remote_service, all_ready)
        if all_ready:
            data.update({
                'port': self.port,
            })
        return data


class Spark(Relation):
    relation_name = 'spark'
    required_keys = ['ready']

    def provide(self, remote_service, all_ready):
        data = super(Spark, self).provide(remote_service, all_ready)
        if all_ready:
            data.update({
                'ready': 'true',
            })
        return data


class Zookeeper(Relation):
    relation_name = 'zookeeper'
    required_keys = ['private-address', 'port']

    def __init__(self, port=None, *args, **kwargs):
        self.port = port  # only needed for provides
        super(Zookeeper, self).__init__(*args, **kwargs)

    def provide(self, remote_service, all_ready):
        data = super(Zookeeper, self).provide(remote_service, all_ready)
        if all_ready:
            data.update({
                'port': self.port,
            })
        return data


class Ganglia(Relation):
    relation_name = 'ganglia'
    required_keys = ['private-address']

    def host(self):
        if not self.is_ready():
            return None
        dict = self.filtered_data().values()[0]
        return dict['private-address']
