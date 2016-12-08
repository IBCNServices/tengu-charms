import json
import shutil

from ..facades import BaseFacade
from ..exc import EnvError


class APIFacade(BaseFacade):
    tag = 'tag'

    def __init__(self, env, version=None):
        super(APIFacade, self).__init__(env, version)
        self.tag_prefixes.append("model")

    def check_op(self, op):
        if 'type' not in op:
            op['type'] = self.name

        if 'version' not in op:
            op['version'] = self.version

        return op


class ModelManager(APIFacade):
    key = "models"
    name = "ModelManager"
    versions = [2]

    def list(self, owner=None):
        """Return a list of available models.

        """
        owner = owner or self.env._creds['user']
        return self.rpc({
            "request": "ListModels",
            "params": {
                "tag": self._format_user_tag(owner),
            }
        })


class Client(APIFacade):
    """Access for annotations.
    """
    key = "client"
    name = "Client"
    versions = [1]

    def __init__(self, env, version=None):
        super(Client, self).__init__(env, version)
        self.annotation = Annotations(env)

    def add_charm(self, charm_url):
        """Add a charm store charm to the environment.

        Example::

          >>> env.add_charm('cs:trusty/mysql-6')
          {}

        charm_url must be a fully qualifed charm url, including
        series and revision.
        """
        return self.rpc({
             "request": "AddCharm",
             "params": {"url": charm_url}})

    def add_machine(self, series="", constraints=None,
                    machine_spec="", parent_id="", container_type=""):
        """Allocate a new machine from the iaas provider or create a container
        on an existing machine.
        """
        if machine_spec:
            err_msg = "Cant specify machine spec with container_type/parent_id"
            assert not (parent_id or container_type), err_msg
            parent_id, container_type = machine_spec.split(":", 1)

        machine_constraints = {}
        if constraints:
            machine_constraints = self._prepare_constraints(constraints)

        params = {
            'series': series,
            'constraints': machine_constraints,
            'container-type': container_type,
            'parent-id': parent_id,
            'jobs': ['JobHostUnits'],
        }
        return self.add_machines([params])['machines'][0]

    def add_machines(self, machines):
        """Allocate multiple machines from the iaas provider.

        See add_machine for format of parameters.
        """
        return self.rpc({
            "request": "AddMachines",
            "params": {
                "params": machines}})

    def agent_version(self):
        """Return the agent version of the juju api server/env."""
        return self.rpc({
            "request": "AgentVersion",
            "params": {}})

    def destroy_machines(self, machine_ids, force=False):
        """Remove the given machines from the environment.

        Will also deallocate from them from the iaas provider.

        If :param: force is provided then the machine and
        units on it will be forcibly destroyed without waiting
        for hook execution state machines.
        """
        params = {"machine-names": machine_ids}
        if force:
            params["force"] = True
        return self.rpc({
            "request": "DestroyMachines",
            "params": params})

    def find_tools(self, major=0, minor=0, series="", arch=""):
        return self.rpc({
            "request": "FindTools",
            "params": {
                "major-version": int(major),
                "minor-version": int(minor),
                "arch": arch,
                "series": series}})

    def get_annotation(self, entity, entity_type):
        names = ["%s-%s" % (entity_type, entity.replace("/", "-"))]
        result = self.annotation.get(names)
        return {'Annotations': result['results'][0]['annotations']}

    def get_env_config(self):
        """Get the environment configuration.

        >>> env.get_env_config()['config'].keys()
        [u'rsyslog-ca-cert',
        u'enable-os-refresh-update', u'firewall-mode',
        u'logging-config', u'enable-os-upgrade',
        u'bootstrap-retry-delay', u'default-series',
        u'bootstrap-user', u'uuid', u'lxc-clone-aufs',
        u'admin-secret', u'set-numa-control-policy', u'agent-version',
        u'disable-network-management', u'ca-private-key', u'type',
        u'bootstrap-timeout', u'development', u'block-remove-object',
        u'tools-metadata-url', u'api-port', u'storage-listen-ip',
        u'block-destroy-environment', u'image-stream',
        u'block-all-changes', u'authorized-keys',
        u'ssl-hostname-verification', u'state-port',
        u'storage-auth-key', u'syslog-port', u'use-sshstorage',
        u'image-metadata-url', u'bootstrap-addresses-delay', u'name',
        u'charm-store-auth', u'agent-metadata-url', u'ca-cert',
        u'test-mode', u'bootstrap-host', u'storage-port',
        u'prefer-ipv6', u'proxy-ssh']
        """
        return self.rpc({
            "request": "ModelGet"})

    def get_env_constraints(self):
        """Get the default constraints associated to the environment.

        >>> env.get_env_constraints()
        {u'Constraints': {}}
        """
        return self.rpc({
            "request": "GetModelConstraints"})

    def get_private_address(self, target):
        """Return the public address of the machine or unit.
        """
        return self.rpc({
            "request": "PrivateAddress",
            "params": {
                "target": target}})

    def get_public_address(self, target):
        # Return the public address of the machine or unit.
        return self.rpc({
            "request": "PublicAddress",
            "params": {
                "target": target}})

    def info(self):
        """Return information about the environment.

        >>> env.info()
        {u'ProviderType': u'manual',
         u'UUID': u'96b7d32a-3c54-4885-836c-98359028a604',
         u'DefaultSeries': u'trusty',
         u'Name': u'ocean'}
        """
        return self.rpc({
            "request": "ModelInfo"})

    def machine_config(self, machine_id, series, arch):
        """Return information needed to render cloudinit for a machine.
        """
        return self.rpc({
            "request": "MachineConfig",
            "params": {
                "machine-id": machine_id,
                "series": series,
                "arch": arch}})

    def provisioning_script(self, machine_id, nonce,
                            data_dir="/var/lib/juju", disable_apt=False):
        """Return a shell script to initialize a machine as part of the env.

        Used inconjunction with :method:register_machine for 'manual' provider
        style machines.

        Common use is to provide this as userdata.
        """
        return self.rpc({
            "request": "ProvisioningScript",
            "params": {
                "machine-id": machine_id,
                "nonce": nonce,
                "data-dir": data_dir,
                "disable-package-commands": disable_apt}})

    def register_machine(self, instance_id, nonce, series, hardware, addrs):
        """Register/Enlist a machine into an environment state.

        The machine will need to have tools installed and subsequently
        connect to the state server with the given nonce
        credentials. The machine_config method can be used to
        construct a suitable set of commands.

        Parameters:

          - nonce: is the initial password for the new machine.
          - addrs: list of ip addresses for the machine.
          - hw: is the hardware characterstics of the machine, applicable keys.
            - Arch
            - Mem
            - RootDisk size
            - CpuCores
            - CpuPower
            - Tags
        """
        params = {
            'series': series,
            'instance-id': instance_id,
            'jobs': ['JobHostUnits'],
            'hardware-characteristics': hardware,
            'addrs': addrs,
            'nonce': nonce,
        }
        return self.register_machines([params])['machines'][0]

    def register_machines(self, machines):
        """Register a set of machines see :method:register_machine."""
        return self.rpc({
            "request": "InjectMachines",
            "params": {
                "machine-params": machines}})

    def resolve_charms(self, names):
        """Resolve an ambigious charm name via the charm store.

        Note this does not resolve the charm revision, only series.

        >>> env.resolve_charms(['rabbitmq-server', 'mysql'])
        {u'URLs': [{u'URL': u'cs:trusty/rabbitmq-server'},
                   {u'URL': u'cs:trusty/mysql'}]}
        """
        if not isinstance(names, (list, tuple)):
            names = [names]
        return self.rpc({
             "request": "ResolveCharms",
             "params": {"references": names}})

    def resolved(self, unit_name, retry=False):
        """Mark a unit's error as resolved, optionally retrying hook execution.
        """
        return self.rpc({
            "request": "Resolved",
            "params": {
                "unit-name": unit_name,
                "retry": retry}})

    def retry_provisioning(self, machines):
        """Mark machines for provisioner to retry iaas provisioning.

        If provisioning failed for a transient reason, this method can
        be utilized to retry provisioning for the given machines.
        """
        return self.rpc({
            "request": "RetryProvisioning",
            "params": {
                "entities": [{"tag": "machine-%s"} for x in machines]}})

    def run(self, command, timeout=None, machines=None,
            services=None, units=None):
        """Run a shell command on the targets (services, units, or machines).
        At least one target must be specified machines || services || units
        """

        assert not (not machines and not services and not units), \
            "You must specify a target"

        rpc_dict = {
            "request": "Run",
            "params": {
                "commands": command,
                "timeout": timeout,
            }
        }

        if machines:
            if not isinstance(machines, (list, tuple)):
                machines = [machines]
            rpc_dict["params"].update({'machines': machines})

        if services:
            if not isinstance(services, (list, tuple)):
                services = [services]
            rpc_dict["params"].update({'applications': services})

        if units:
            if not isinstance(units, (list, tuple)):
                units = [units]
            rpc_dict["params"].update({'units': units})

        return self.rpc(rpc_dict)

    def run_on_all_machines(self, command, timeout=None):
        """Run the given shell command on all machines in the environment."""
        return self.rpc({
            "request": "RunOnAllMachines",
            "params": {"commands": command,
                       "timeout": timeout}})

    def set_env_agent_version(self, version):
        """Upgrade an environment to the given agent version."""
        return self.rpc({
            "request": "SetModelAgentVersion",
            "params": {"version": version}})

    def set_env_config(self, config):
        """Update the environment configuration with the given mapping.

        *Note* that several of these properties are read-only or
        configurable only at a boot time.
        """
        return self.rpc({
            "request": "ModelSet",
            "params": {"config": config}})

    def set_env_constraints(self, constraints):
        """Set the default environment constraints.
        """
        return self.rpc({
            "request": "SetModelConstraints",
            "params": {
                "application": "",
                "constraints": self._prepare_constraints(constraints)}})

    def set_annotation(self, entity, entity_type, annotation):
        name = "%s-%s" % (entity_type, entity.replace("/", "-"))
        return self.annotation.set([(name, annotation)])

    def status(self, filters=()):
        """Return the state of the environment.

        Includes information on machines, services, relations, and units
        in the environment.

        filters can be specified as a sequence of names to focus on
        particular services or units.

        Note this only loosely corresponds to cli status output format.
        """
        if not isinstance(filters, (list, tuple)):
            filters = [filters]
        return self.rpc({
            'request': 'FullStatus',
            'params': {'patterns': filters}})

    def unset_env_config(self, keys):
        """Reset the given environment config to the default juju values.

        """
        return self.rpc({
            "request": "ModelUnset",
            "params": {"keys": keys}})


class UserManager(APIFacade):
    key = "users"
    name = "UserManager"
    versions = [1]

    def add(self, users):
        """
        param users: a list structure with each element corresponding to
        a dict with keys for 'username', 'display-name', 'password'.
        alternatively a dict to add a single user.

        Example::

          >>> env.users.add({'username': 'mike',
                      'display-name': 'Michael Smith',
                      'password': 'zebramoon'})
          {u'results': [{u'tag': u'user-mike@local'}]}
        """
        if isinstance(users, dict):
            users = [users]
        return self.rpc({
            "request": "AddUser",
            "params": {"users": users}})

    def enable(self, names):
        """
        params names: list of usernames to enable or disable.
        """
        return self.rpc({
            "request": "EnableUser",
            "params": {"entities": self._format_user_names(names)}})

    def disable(self, names):
        """
        params names: list of usernames to enable or disable.
        """
        return self.rpc({
            "request": "DisableUser",
            "params": {"entities": self._format_user_names(names)}})

    def list(self, names=(), disabled=True):
        """List information about the given users in the environment.

        If no names are passed then return information about all users.

        Example::

          >>> env.users.list()
          {u'results': [{u'result': {
                u'username': u'admin',
                u'last-connection':
                u'2015-01-20T14:45:47Z',
                u'disabled': False,
                u'date-created': u'2015-01-19T22:12:35Z',
                u'display-name': u'admin',
                u'created-by': u'admin'}}]}

        also re disabled see bug on includedisabled on core.
        """
        return self.rpc({
            "request": "UserInfo",
            "params": {"entities": self._format_user_names(names),
                       "include-disabled": disabled}})

    def set_password(self, entities):
        """params entities:  a list of dictionaries with
        'username' and 'password', alternatively a single
        dicitonary.
        """
        if isinstance(entities, dict):
            entities = [entities]

        users = []

        for e in entities:
            if 'username' not in e or 'password' not in e:
                raise ValueError(
                    "Invalid parameter for set password %s" % entities)
            users.append(
                {'tag': self._format_user_tag(e['username']),
                 'password': e['password']})

        return self.rpc({
            "request": "SetPassword",
            "params": {"changes": users}})


class Charms(APIFacade):
    """Access information about charms extant in the environment.

    Note Currently broken per bug: http://pad.lv/1414086
    """
    key = "charms"
    name = "Charms"
    versions = [2]

    def info(self, charm_url):
        """Retrieve information about a charm in the environment.

        Charm url must be fully qualified.

        >>> env.charms.info('cs:~hazmat/trusty/etcd-6')
        """
        return self.rpc({
            "request": "CharmInfo",
            "params": {"url": charm_url}})

    def list(self, names=()):
        """Retrieve all charms with the given names or all charms.

        >>> env.charms.list('etcd')

        """
        if not isinstance(names, (list, tuple)):
            names = [names]
        return self.rpc({
            "request": "List",
            "params": {"names": names}})


class Annotations(APIFacade):
    """Get and set annotations enmass on entities.

    Note Currently broken per bug: http://pad.lv/1414086
    """
    key = "annotations"
    name = "Annotations"
    versions = [2]

    def get(self, names):
        """Get annotations on a set of names.

        Names can be a singelton or list, ideally in tag format (type-$id) ala
        unit-mysql/0, machine-22, else this method will attempt to introspect
        $id and utilize the appropriate type prefix to construct a tag.

        Note the tag format for the environment itself uses the environment
        uuid.

        >>> env.annotations.get(['cs:~hazmat/trusty/etcd-6'])
        {u'Results': [{u'EntityTag': u'charm-cs:~hazmat/trusty/etcd-6',
                       u'Annotations': {u'vcs': u'bzr'},
                       u'Error': {u'Error': None}}]}
        """
        if not isinstance(names, (list, tuple)):
            names = [names]
        entities = map(self._format_tag, names)

        return self.rpc({
            'request': 'Get',
            'params': {
                'entities': list(entities)}})

    def set(self, annotations):
        """Set annotations on a set of entities.

        Format is a sequence of sequences (name, annotation_dict)

        Entity tag format is inferred if possible.

        >>> env.annotations.set([
            ('charm-cs:~hazmat/trusty/etcd-6', {'vcs': 'bzr'})])
        {u'Results': []}

        >>> env.annotations.set([('mysql', {'x': 1, 'y': 2})])
        {u'Results': []}
        """
        e_a = []
        for a in annotations:
            if not isinstance(a, (list, tuple)) and len(a) == 2:
                raise ValueError(
                    "Annotation values should be a list/tuple"
                    "of name, dict %s" % a)
            n, d = a
            if not isinstance(d, dict):
                raise ValueError(
                    "Annotation values should be a list/tuple"
                    "of name, dict %s" % a)
            e_a.append({'entity': self._format_tag_name(n),
                        'annotations': d})
        return self.rpc({
            'request': 'Set',
            'params': {'annotations': e_a}})


class KeyManager(APIFacade):
    """
    Note: Key management implementation is work in progress atm, the
    api is scoped at a user level but the implementation allows for
    global access to all users. ie. any key added has root access to the
    environment for all users.
    """
    key = "keys"
    name = "KeyManager"
    versions = [1]

    def list(self, names, mode=True):
        """ Return a set of ssh keys or fingerprints for the given users.

        Mode: is a boolean, true is show the full key, false for fingerprints.

        >>> env.keys.list('user-admin', mode=False)
         {u'Results': [
             {u'Result': [u'42:d1:22:a4:f3:38:b2:e8:ce... (juju-system-key)']]
              u'Error': None}]}
        """
        return self.rpc({
            "request": "ListKeys",
            "params": {"entities": self._format_user_names(names),
                       "mode": mode}})

    def add(self, user, keys):
        return self.rpc({
            "request": "AddKeys",
            "params": {"user": user,
                       "keys": keys}})

    def delete(self, user, keys):
        """Remove the given ssh keys for the given user.

        Key parameters pass in should correspond to fingerprints or comment.
        """
        return self.rpc({
            "request": "DeleteKeys",
            "params": {"user": user,
                       "keys": keys}})

    def import_keys(self, user, keys):
        """Import env user's keys using ssh-import-id.

        >>> env.keys.import_keys('admin', 'gh:kapilt')
        """
        return self.rpc({
            "request": "ImportKeys",
            "params": {"user": user,
                       "keys": keys}})


class Backups(APIFacade):
    key = "backups"
    name = "Backups"
    versions = [1]

    def create(self, notes):
        """Create in this client is synchronous. It returns after
        the backup is taken.

        >>> env.backups.create('abc')
        {u'Machine': u'0',
        u'Version': u'1.23-alpha1.1',
        u'Started': u'2015-01-22T18:05:30.014657514Z',
        u'Checksum': u'nDAiKQmhrpiB2W5n/OijqUJtGYE=',
        u'ChecksumFormat': u'SHA-1, base64 encoded',
        u'Hostname': u'ocean-0',
        u'Environment': u'28d91a3d-b50d-4549-80a1-165fe1cc62db',
        u'Finished': u'2015-01-22T18:05:38.11633437Z',
        u'Stored': u'2015-01-22T18:05:42Z',
        u'Notes': u'abc',
        u'ID': u'20150122-180530.28d91a3d-b50d-4549-80a1-165fe1cc62db',
        u'Size': 17839021}
        """
        return self.rpc({
            "request": "Create",
            "params": {"notes": notes}})

    def info(self, backup_id):
        """Get info on a given backup. Given all backup info is returned
        on 'list' this method is exposed just for completeness.

        >>> env.backups.info(
            ...   "20150122-180530.28d91a3d-b50d-4549-80a1-165fe1cc62db")
        {u'Checksum': u'nDAiKQmhrpiB2W5n/OijqUJtGYE=',
        u'ChecksumFormat': u'SHA-1, base64 encoded',
        u'Environment': u'28d91a3d-b50d-4549-80a1-165fe1cc62db',
        u'Finished': u'2015-01-22T18:05:38Z',
        u'Hostname': u'ocean-0',
        u'ID': u'20150122-180530.28d91a3d-b50d-4549-80a1-165fe1cc62db',
        u'Machine': u'0',
        u'Notes': u'abc',
        u'Size': 17839021,
        u'Started': u'2015-01-22T18:05:30Z',
        u'Stored': u'2015-01-22T18:05:42Z',
        u'Version': u'1.23-alpha1.1'}
         """
        return self.rpc({
            "request": "Info",
            "params": {"id": backup_id}})

    def list(self):
        """ List all the backups and their info.

        >>> env.backups.list()
        {u'List': [{u'Checksum': u'nDAiKQmhrpiB2W5n/OijqUJtGYE=',
            u'ChecksumFormat': u'SHA-1, base64 encoded',
            u'Environment': u'28d91a3d-b50d-4549-80a1-165fe1cc62db',
            u'Finished': u'2015-01-22T18:05:38Z',
            u'Hostname': u'ocean-0',
            u'ID': u'20150122-180530.28d91a3d-b50d-4549-80a1-165fe1cc62db',
            u'Machine': u'0',
            u'Notes': u'abc',
            u'Size': 17839021,
            u'Started': u'2015-01-22T18:05:30Z',
            u'Stored': u'2015-01-22T18:05:42Z',
            u'Version': u'1.23-alpha1.1'}]}
        """
        return self.rpc({
            "request": "List",
            "params": {}})

    def remove(self, backup_id):
        """ Remove the given backup.
        >>> env.backups.remove(
        ...    '20150122-181136.28d91a3d-b50d-4549-80a1-165fe1cc62db')
        {}
        """
        return self.rpc({
            "request": "Remove",
            "params": {"id": backup_id}})

    def download(self, backup_id, path=None, fh=None):
        """ Download the given backup id to the given path or file handle.

        TODO:
         - Progress callback (its chunked encoding so don't know size)
           bug on core to send size: http://pad.lv/1414021
         - Checksum validation ('digest' header has sha checksum)
        """
        if fh is None and path is None:
            raise ValueError("Please specify path or file")
        conn, headers, path_prefix = self.rpc._http_conn()
        headers['Content-Type'] = 'application/json'
        if path:
            fh = open(path, 'wb')
        with fh:
            url_path = "%s/backups" % path_prefix
            conn.request(
                "GET", url_path, json.dumps({"ID": backup_id}), headers)
            response = conn.getresponse()
            if response.status != 200:
                raise EnvError({"error": response.read()})
            shutil.copyfileobj(response, fh, 2 ** 15)
            size = fh.tell()
        return size

    # No restore in trunk yet, so waiting.
    def upload(self):
        raise NotImplementedError()


class ImageManager(APIFacade):
    """Find information about the images available to a given environment.

    This information ultimately derives from the simple streams image metadata
    for the environment.
    """
    key = "images"
    name = "ImageManager"
    versions = [2]

    def list(self, image_specs=()):
        """List information about the matching images.

        image_spec = {'Kind': 'kind', 'Series': 'trusty', 'Arch': 'amd64'}
        """
        if not isinstance(image_specs, (list, tuple)):
            image_specs = [image_specs]
        return self.rpc({
            'request': 'ListImages',
            'params': {'images': image_specs}})

    def delete(self, image_specs):
        """Delete the specified image

        image_spec = {'Kind': 'kind', 'Series': 'trusty', 'Arch': 'amd64'}
        """
        if not isinstance(image_specs, (list, tuple)):
            image_specs = [image_specs]

        return self.rpc({
            'request': 'DeleteImages',
            'params': {'images': image_specs}})


class HA(APIFacade):
    """Manipulate the ha properties of an environment.
    """
    key = "ha"
    name = "HighAvailability"
    versions = [2]

    def ensure_availability(self, num_state_servers, series=None,
                            constraints=None, placement=None):
        """Enable multiple state servers on machines.

        Note placement api is specifically around instance placement, ie
        it can specify zone or maas name. Existing environment machines
        can't be designated state servers :-(
        """
        return self.rpc({
            'request': 'EnableHA',
            'params': {
                'specs': [{
                    'model-tag': "model-%s" % self.env._env_uuid,
                    'num-controllers': int(num_state_servers),
                    'series': series,
                    'constraints': self._format_constraints(constraints),
                    'placement': placement}]}})


class Actions(APIFacade):
    """Api to interact with charm defined operations.

    See https://juju.ubuntu.com/docs/actions.html for more details.
    """
    key = "actions"
    name = "Action"
    versions = [2]

    # Query services for available action definitions
    def service_actions(self, services):
        """Return available actions for the given services.
        """
        return self.rpc({
            "request": "ServicesCharmActions",
            "params": {
                "entities": self._format_receivers(services)}})

    def enqueue_units(self, units, action_name, params):
        """Enqueue an action on a set of units."""
        if not isinstance(units, (list, tuple)):
            units = [units]
        actions = []
        for u in units:
            if not u.startswith('unit-'):
                u = "unit-%s" % u
            actions.append({
                'tag': '',
                'name': action_name,
                'receiver': u,
                'parameters': params})
        return self._enqueue(actions)

    def _enqueue(self, actions):
        return self.rpc({
            'request': 'Enqueue',
            'params': {'actions': actions}})

    def cancel(self, action_ids):
        """Cancel a pending action by id."""
        return self.rpc({
            'request': 'Cancel',
            "params": {
                "entities": action_ids}})

    # Query action info
    def info(self, action_ids):
        """Return information on a set of actions."""
        return self.rpc({
            'request': 'Actions',
            'params': {
                'entities': action_ids}})

    def find(self, prefixes):
        """Find actions by prefixes on their ids...
        """
        if not isinstance(prefixes, (list, tuple)):
            prefixes = [prefixes]
        return self.rpc({
            "request": "FindActionTagsByPrefix",
            "params": {
                "prefixes": prefixes}})

    # Query actions instances by receiver.
    def all(self, receivers):
        """Return all actions for the given receivers."""
        return self.rpc({
            'request': 'ListAll',
            "params": {
                "entities": self._format_receivers(receivers)}})

    def pending(self, receivers):
        """Return all pending actions for the given receivers."""
        return self.rpc({
            'request': 'ListPending',
            "params": {
                "entities": self._format_receivers(receivers)}})

    def completed(self, receivers):
        """Return all completed actions for the given receivers."""
        return self.rpc({
            'request': 'ListCompleted',
            "params": {
                "entities": self._format_receivers(receivers)}})

    def _format_receivers(self, names):
        if not isinstance(names, (list, tuple)):
            names = [names]
        receivers = []
        for n in names:
            if n.startswith('unit-') or n.startswith('service-'):
                pass
            elif '/' in n:
                n = "unit-%s" % n
            else:
                n = "service-%s" % n
            receivers.append({"tag": n})
        return receivers


class Application(APIFacade):
    """Access for services.
    """
    key = "application"
    name = "Application"
    versions = [1]

    def deploy(self, service_name, charm_url, num_units=1,
               config=None, constraints=None, machine_spec=None):
        """Deploy a service.

        To use with local charms, the charm must have previously
        been added with a call to add_local_charm or add_local_charm_dir.
        """
        svc_config = {}
        if config:
            svc_config = self._prepare_strparams(config)

        svc_constraints = {}
        if constraints:
            svc_constraints = self._prepare_constraints(constraints)

        svc_placement = []
        if machine_spec:
            svc_placement = [self._prepare_placement(machine_spec)]

        return self.rpc({
             "request": "Deploy",
             "params": {
               "applications": [{
                 "application": service_name,
                 "charm-url": charm_url,
                 "placement": svc_placement,
                 "num-units": num_units,
                 "config": svc_config,
                 "constraints": svc_constraints,
                 }]}})

    def set(self, service_name, config):
        """Set a service's configuration."""
        assert isinstance(config, dict)
        svc_config = self._prepare_strparams(config)
        return self.rpc({
            "request": "Set",
            "params": {
                "application": service_name,
                "options": svc_config}})

    def unset(self, service_name, config_keys):
        """Unset configuration values of a service to restore charm defaults.
        """
        return self.rpc({
            "request": "ApplicationUnset",
            "params": {
                "application": service_name,
                "options": config_keys}})

    def set_charm(self, service_name, charm_url, force=False):
        """Set the charm url for a service.
        """
        return self.rpc({
            "request": "SetCharm",
            "params": {
                "application": service_name,
                "charm-url": charm_url,
                # Force both units and series
                "force-units": force,
                "force-series": force}})

    def get(self, service_name):
        """Returns dict of Charm, Config, Constraints, Service keys.

        Charm -> charm used by service
        Service -> service name
        Config -> Currently configured options and descriptions
        Constraints -> Constraints set on service (not environment inherited).
        """
        return self.rpc({
             "request": "Get",
             "params": {
                 "application": service_name}})

    def get_config(self, service_name):
        """Returns service configuration.
        """
        return self.get(service_name)['config']

    def get_constraints(self, service_name):
        return self.rpc({
             "request": "GetConstraints",
             "params": {
                 "application": service_name}})['constraints']

    def set_constraints(self, service_name, constraints):
        return self.rpc({
             "request": "SetConstraints",
             "params": {
                 "application": service_name,
                 "constraints": self._prepare_constraints(constraints)}})

    def destroy_service(self, service_name):
        """Destroy a service and all of its units.

        On versions of juju 1.22+ this will also deallocate the iaas
        machine resources those units were assigned to if they
        were the only unit residing on the machine.
        """
        return self.rpc({
            "request": "Destroy",
            "params": {
                "application": service_name}})

    def expose(self, service_name):
        """Provide external access to a given service.

        Will manipulate the iaas layer's firewall machinery
        to enabmle public access from outside of the environment.
        """
        return self.rpc({
            "request": "Expose",
            "params": {
                "application": service_name}})

    def unexpose(self, service_name):
        """Remove external access to a given service.

        Will manipulate the iaas layer's firewall machinery
        to disable public access from outside of the environment.
        """
        return self.rpc({
            "request": "Unexpose",
            "params": {
                "application": service_name}})

    # Relations
    def valid_relation_names(self, service_name):
        """All possible relation names of a service.

        Per its charm metadata.
        """
        return self.rpc({
            "request": "CharmRelations",
            "params": {
                "application": service_name}})

    def add_relation(self, endpoint_a, endpoint_b):
        """Add a relation between two endpoints."""
        return self.rpc({
            'request': 'AddRelation',
            'params': {
                'endpoints': [endpoint_a, endpoint_b]
            }})

    def remove_relation(self, endpoint_a, endpoint_b):
        """Remove a relation between two endpoints."""
        return self.rpc({
            'request': 'DestroyRelation',
            'params': {
                'endpoints': [endpoint_a, endpoint_b]
            }})

    # Units
    def add_units(self, service_name, num_units=1):
        """Add n units of a given service.

        Machines will be allocated from the iaas provider
        or unused machines in the environment that
        match the service's constraints.
        """
        return self.rpc({
            "request": "AddUnits",
            "params": {
                "application": service_name,
                "num-units": num_units}})

    def add_unit(self, service_name, machine_spec=None):
        """Add a unit of the given service

        Optionally with placement onto a given existing
        machine or a new container.
        """
        svc_placement = []
        if machine_spec:
            svc_placement = [self._prepare_placement(machine_spec)]

        params = {
            "application": service_name,
            "placement": svc_placement,
            "num-units": 1}
        return self.rpc({
            "request": "AddUnits",
            "params": params})

    def remove_units(self, unit_names):
        """Remove the given service units.
        """
        return self.rpc({
            "request": "DestroyUnits",
            "params": {
                "unit-names": unit_names}})
