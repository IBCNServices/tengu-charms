import json
import shutil

from ..facades import BaseFacade
from ..exc import EnvError


class APIFacade(BaseFacade):
    def __init__(self, env, version=None):
        super(APIFacade, self).__init__(env, version)
        self.tag_prefixes.append("environment")

    def check_op(self, op):
        if 'Type' not in op:
            op['Type'] = self.name

        if 'Version' not in op:
            op['Version'] = self.version

        return op


class Client(APIFacade):
    """Access for annotations.
    """
    key = "client"
    name = "Client"
    versions = [0]

    def add_charm(self, charm_url):
        """Add a charm store charm to the environment.

        Example::

          >>> env.add_charm('cs:trusty/mysql-6')
          {}

        charm_url must be a fully qualifed charm url, including
        series and revision.
        """
        return self.rpc({
             "Request": "AddCharm",
             "Params": {"URL": charm_url}})

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
            'Series': series,
            'Constraints': machine_constraints,
            'ContainerType': container_type,
            'ParentId': parent_id,
            'Jobs': ['JobHostUnits'],
        }
        return self.add_machines([params])['Machines'][0]

    def add_machines(self, machines):
        """Allocate multiple machines from the iaas provider.

        See add_machine for format of parameters.
        """
        return self.rpc({
            "Request": "AddMachines",
            "Params": {
                "MachineParams": machines}})

    def agent_version(self):
        """Return the agent version of the juju api server/env."""
        return self.rpc({
            "Request": "AgentVersion",
            "Params": {}})

    def destroy_machines(self, machine_ids, force=False):
        """Remove the given machines from the environment.

        Will also deallocate from them from the iaas provider.

        If :param: force is provided then the machine and
        units on it will be forcibly destroyed without waiting
        for hook execution state machines.
        """
        params = {"MachineNames": machine_ids}
        if force:
            params["Force"] = True
        return self.rpc({
            "Request": "DestroyMachines",
            "Params": params})

    def find_tools(self, major=0, minor=0, series="", arch=""):
        return self.rpc({
            "Request": "FindTools",
            "Params": {
                "MajorVersion": int(major),
                "MinorVersion": int(minor),
                "Arch": arch,
                "Series": series}})

    def get_annotation(self, entity, entity_type):
        return self.rpc({
            "Request": "GetAnnotations",
            "Params": {
                "Tag": "%s-%s" % (entity_type, entity.replace("/", "-"))}})

    def get_env_config(self):
        """Get the environment configuration.

        >>> env.get_env_config()['Config'].keys()
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
            "request": "EnvironmentGet"})

    def get_env_constraints(self):
        """Get the default constraints associated to the environment.

        >>> env.get_env_constraints()
        {u'Constraints': {}}
        """
        return self.rpc({
            "Request": "GetEnvironmentConstraints"})

    def get_private_address(self, target):
        """Return the public address of the machine or unit.
        """
        return self.rpc({
            "Request": "PrivateAddress",
            "Params": {
                "Target": target}})

    def get_public_address(self, target):
        # Return the public address of the machine or unit.
        return self.rpc({
            "Request": "PublicAddress",
            "Params": {
                "Target": target}})

    def info(self):
        """Return information about the environment.

        >>> env.info()
        {u'ProviderType': u'manual',
         u'UUID': u'96b7d32a-3c54-4885-836c-98359028a604',
         u'DefaultSeries': u'trusty',
         u'Name': u'ocean'}
        """
        return self.rpc({
            "Request": "EnvironmentInfo"})

    def machine_config(self, machine_id, series, arch):
        """Return information needed to render cloudinit for a machine.
        """
        return self.rpc({
            "Request": "MachineConfig",
            "Params": {
                "MachineId": machine_id,
                "Series": series,
                "Arch": arch}})

    def provisioning_script(self, machine_id, nonce,
                            data_dir="/var/lib/juju", disable_apt=False):
        """Return a shell script to initialize a machine as part of the env.

        Used inconjunction with :method:register_machine for 'manual' provider
        style machines.

        Common use is to provide this as userdata.
        """
        return self.rpc({
            "Request": "ProvisioningScript",
            "Params": {
                "MachineId": machine_id,
                "Nonce": nonce,
                "DataDir": data_dir,
                "DisablePackageCommands": disable_apt}})

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
            'Series': series,
            'InstanceId': instance_id,
            'Jobs': ['JobHostUnits'],
            'HardwareCharacteristics': hardware,
            'Addrs': addrs,
            'Nonce': nonce,
        }
        return self.register_machines([params])['machines'][0]

    def register_machines(self, machines):
        """Register a set of machines see :method:register_machine."""
        return self.rpc({
            "Request": "InjectMachines",
            "Params": {
                "MachineParams": machines}})

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
             "Request": "ResolveCharms",
             "Params": {"References": names}})

    def resolved(self, unit_name, retry=False):
        """Mark a unit's error as resolved, optionally retrying hook execution.
        """
        return self.rpc({
            "Request": "Resolved",
            "Params": {
                "UnitName": unit_name,
                "Retry": retry}})

    def retry_provisioning(self, machines):
        """Mark machines for provisioner to retry iaas provisioning.

        If provisioning failed for a transient reason, this method can
        be utilized to retry provisioning for the given machines.
        """
        return self.rpc({
            "Request": "RetryProvisioning",
            "Params": {
                "Entities": [{"Tag": "machine-%s"} for x in machines]}})

    def run(self, command, timeout=None, machines=None,
            services=None, units=None):
        """Run a shell command on the targets (services, units, or machines).
        At least one target must be specified machines || services || units
        """

        assert not (not machines and not services and not units), \
            "You must specify a target"

        rpc_dict = {
            "Request": "Run",
            "Params": {
                "Commands": command,
                "Timeout": timeout,
            }
        }

        if machines:
            if not isinstance(machines, (list, tuple)):
                machines = [machines]
            rpc_dict["Params"].update({'Machines': machines})

        if services:
            if not isinstance(services, (list, tuple)):
                services = [services]
            rpc_dict["Params"].update({'Services': services})

        if units:
            if not isinstance(units, (list, tuple)):
                units = [units]
            rpc_dict["Params"].update({'Units': units})

        return self.rpc(rpc_dict)

    def run_on_all_machines(self, command, timeout=None):
        """Run the given shell command on all machines in the environment."""
        return self.rpc({
            "Request": "RunOnAllMachines",
            "Params": {"Commands": command,
                       "Timeout": timeout}})

    def set_env_agent_version(self, version):
        """Upgrade an environment to the given agent version."""
        return self.rpc({
            "Request": "SetEnvironmentAgentVersion",
            "Params": {"Version": version}})

    def set_env_config(self, config):
        """Update the environment configuration with the given mapping.

        *Note* that several of these properties are read-only or
        configurable only at a boot time.
        """
        return self.rpc({
            "Request": "EnvironmentSet",
            "Params": {"Config": config}})

    def set_env_constraints(self, constraints):
        """Set the default environment constraints.
        """
        return self.rpc({
            "Request": "SetEnvironmentConstraints",
            "Params": {
                "ServiceName": "",
                "Constraints": self._prepare_constraints(constraints)}})

    def set_annotation(self, entity, entity_type, annotation):
        """
        Set annotations on an entity.

        Valid entity types for this method are 'service', 'unit',
        'machine', 'environment'.

        Use the annotation facade if available as it supports more
        entities, and setting and getting values enmass.
        """
        # valid entity types
        a = self._prepare_strparams(annotation)
        return self.rpc({
            "Request": "SetAnnotations",
            "Params": {
                "Tag": entity_type + '-' + entity.replace("/", "-"),
                "Pairs": a}})

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
            'Request': 'FullStatus',
            'Params': {'Patterns': filters}})

    def unset_env_config(self, keys):
        """Reset the given environment config to the default juju values.

        """
        return self.rpc({
            "Request": "EnvironmentUnset",
            "Params": {"Keys": keys}})


class UserManager(APIFacade):
    key = "users"
    name = "UserManager"
    versions = [0]

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
            "Request": "AddUser",
            "Params": {"Users": users}})

    def enable(self, names):
        """
        params names: list of usernames to enable or disable.
        """
        return self.rpc({
            "Request": "EnableUser",
            "Params": {"Entities": self._format_user_names(names)}})

    def disable(self, names):
        """
        params names: list of usernames to enable or disable.
        """
        return self.rpc({
            "Request": "DisableUser",
            "Params": {"Entities": self._format_user_names(names)}})

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
            "Request": "UserInfo",
            "Params": {"Entities": self._format_user_names(names),
                       "IncludeDisabled": disabled}})

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
                {'Tag': self._format_user_tag(e['username']),
                 'Password': e['password']})

        return self.rpc({
            "Request": "SetPassword",
            "Params": {"Changes": users}})


class Charms(APIFacade):
    """Access information about charms extant in the environment.

    Note Currently broken per bug: http://pad.lv/1414086
    """
    key = "charms"
    name = "Charms"
    versions = [1]

    def info(self, charm_url):
        """Retrieve information about a charm in the environment.

        Charm url must be fully qualified.

        >>> env.charms.info('cs:~hazmat/trusty/etcd-6')
        """
        return self.rpc({
            "Request": "CharmInfo",
            "Params": {"CharmURL": charm_url}})

    def list(self, names=()):
        """Retrieve all charms with the given names or all charms.

        >>> env.charms.list('etcd')

        """
        if not isinstance(names, (list, tuple)):
            names = [names]
        return self.rpc({
            "Request": "List",
            "Params": {"Names": names}})


class Annotations(APIFacade):
    """Get and set annotations enmass on entities.

    Note Currently broken per bug: http://pad.lv/1414086
    """
    key = "annotations"
    name = "Annotations"
    versions = [1]

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
            'Request': 'Get',
            'Params': {
                'Entities': list(entities)}})

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
            e_a.append({'EntityTag': self._format_tag_name(n),
                        'Annotations': d})
        return self.rpc({
            'Request': 'Set',
            'Params': {'Annotations': e_a}})


class KeyManager(APIFacade):
    """
    Note: Key management implementation is work in progress atm, the
    api is scoped at a user level but the implementation allows for
    global access to all users. ie. any key added has root access to the
    environment for all users.
    """
    key = "keys"
    name = "KeyManager"
    versions = [0]

    def list(self, names, mode=True):
        """ Return a set of ssh keys or fingerprints for the given users.

        Mode: is a boolean, true is show the full key, false for fingerprints.

        >>> env.keys.list('user-admin', mode=False)
         {u'Results': [
             {u'Result': [u'42:d1:22:a4:f3:38:b2:e8:ce... (juju-system-key)']]
              u'Error': None}]}
        """
        return self.rpc({
            "Request": "ListKeys",
            "Params": {"Entities": self._format_user_names(names),
                       "Mode": mode}})

    def add(self, user, keys):
        return self.rpc({
            "Request": "AddKeys",
            "Params": {"User": user,
                       "Keys": keys}})

    def delete(self, user, keys):
        """Remove the given ssh keys for the given user.

        Key parameters pass in should correspond to fingerprints or comment.
        """
        return self.rpc({
            "Request": "DeleteKeys",
            "Params": {"User": user,
                       "Keys": keys}})

    def import_keys(self, user, keys):
        """Import env user's keys using ssh-import-id.

        >>> env.keys.import_keys('admin', 'gh:kapilt')
        """
        return self.rpc({
            "Request": "ImportKeys",
            "Params": {"User": user,
                       "Keys": keys}})


class Backups(APIFacade):
    key = "backups"
    name = "Backups"
    versions = [0]

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
            "Request": "Create",
            "Params": {"Notes": notes}})

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
            "Request": "Info",
            "Params": {"Id": backup_id}})

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
            "Request": "List",
            "Params": {}})

    def remove(self, backup_id):
        """ Remove the given backup.
        >>> env.backups.remove(
        ...    '20150122-181136.28d91a3d-b50d-4549-80a1-165fe1cc62db')
        {}
        """
        return self.rpc({
            "Request": "Remove",
            "Params": {"Id": backup_id}})

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
                raise EnvError({"Error": response.read()})
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
    versions = [1]

    def list(self, image_specs=()):
        """List information about the matching images.

        image_spec = {'Kind': 'kind', 'Series': 'trusty', 'Arch': 'amd64'}
        """
        if not isinstance(image_specs, (list, tuple)):
            image_specs = [image_specs]
        return self.rpc({
            'Request': 'ListImages',
            'Params': {'Images': image_specs}})

    def delete(self, image_specs):
        """Delete the specified image

        image_spec = {'Kind': 'kind', 'Series': 'trusty', 'Arch': 'amd64'}
        """
        if not isinstance(image_specs, (list, tuple)):
            image_specs = [image_specs]

        return self.rpc({
            'Request': 'DeleteImages',
            'Params': {'Images': image_specs}})


class HA(APIFacade):
    """Manipulate the ha properties of an environment.
    """
    key = "ha"
    name = "HighAvailability"
    versions = [1]

    def ensure_availability(self, num_state_servers, series=None,
                            constraints=None, placement=None):
        """Enable multiple state servers on machines.

        Note placement api is specifically around instance placement, ie
        it can specify zone or maas name. Existing environment machines
        can't be designated state servers :-(
        """
        return self.rpc({
            'Request': 'EnsureAvailability',
            'Params': {
                'EnvironTag': "environment-%s" % self.env._env_uuid,
                'NumStateServers': int(num_state_servers),
                'Series': series,
                'Constraints': self._format_constraints(constraints),
                'Placement': placement}})


class Actions(APIFacade):
    """Api to interact with charm defined operations.

    See https://juju.ubuntu.com/docs/actions.html for more details.
    """
    key = "actions"
    name = "Action"
    versions = [0]

    # Query services for available action definitions
    def service_actions(self, services):
        """Return available actions for the given services.
        """
        return self.rpc({
            "Request": "ServicesCharmActions",
            "Params": {
                "Entities": self._format_receivers(services)}})

    def enqueue_units(self, units, action_name, params):
        """Enqueue an action on a set of units."""
        if not isinstance(units, (list, tuple)):
            units = [units]
        actions = []
        for u in units:
            if not u.startswith('unit-'):
                u = "unit-%s" % u
            actions.append({
                'Tag': '',
                'Name': action_name,
                'Receiver': u,
                'Parameters': params})
        return self._enqueue(actions)

    def _enqueue(self, actions):
        return self.rpc({
            'Request': 'Enqueue',
            'Params': {'Actions': actions}})

    def cancel(self, action_ids):
        """Cancel a pending action by id."""
        return self.rpc({
            'Request': 'Cancel',
            "Params": {
                "Entities": action_ids}})

    # Query action info
    def info(self, action_ids):
        """Return information on a set of actions."""
        return self.rpc({
            'Request': 'Actions',
            'Params': {
                'Entities': action_ids}})

    def find(self, prefixes):
        """Find actions by prefixes on their ids...
        """
        if not isinstance(prefixes, (list, tuple)):
            prefixes = [prefixes]
        return self.rpc({
            "Request": "FindActionTagsByPrefix",
            "Params": {
                "Prefixes": prefixes}})

    # Query actions instances by receiver.
    def all(self, receivers):
        """Return all actions for the given receivers."""
        return self.rpc({
            'Request': 'ListAll',
            "Params": {
                "Entities": self._format_receivers(receivers)}})

    def pending(self, receivers):
        """Return all pending actions for the given receivers."""
        return self.rpc({
            'Request': 'ListPending',
            "Params": {
                "Entities": self._format_receivers(receivers)}})

    def completed(self, receivers):
        """Return all completed actions for the given receivers."""
        return self.rpc({
            'Request': 'ListCompleted',
            "Params": {
                "Entities": self._format_receivers(receivers)}})

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
            receivers.append({"Tag": n})
        return receivers


class Service(APIFacade):
    """Access for services.
    """
    key = "service"
    name = "Service"
    versions = [0]

    # Service
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

        return self.rpc(
            {"Type": "Client",
             "Request": "ServiceDeploy",
             "Params": {
                 "ServiceName": service_name,
                 "CharmURL": charm_url,
                 "NumUnits": num_units,
                 "Config": svc_config,
                 "Constraints": svc_constraints,
                 "ToMachineSpec": machine_spec}})

    def set_config(self, service_name, config):
        """Set a service's configuration."""
        assert isinstance(config, dict)
        svc_config = self._prepare_strparams(config)
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceSet",
            "Params": {
                "ServiceName": service_name,
                "Options": svc_config}})

    def unset_config(self, service_name, config_keys):
        """Unset configuration values of a service to restore charm defaults.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceUnset",
            "Params": {
                "ServiceName": service_name,
                "Options": config_keys}})

    def set_charm(self, service_name, charm_url, force=False):
        """Set the charm url for a service.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceSetCharm",
            "Params": {
                "ServiceName": service_name,
                "CharmUrl": charm_url,
                "Force": force}})

    def get_service(self, service_name):
        """Returns dict of Charm, Config, Constraints, Service keys.

        Charm -> charm used by service
        Service -> service name
        Config -> Currently configured options and descriptions
        Constraints -> Constraints set on service (not environment inherited).
        """
        return self.rpc(
            {"Type": "Client",
             "Request": "ServiceGet",
             "Params": {
                 "ServiceName": service_name}})

    def get_config(self, service_name):
        """Returns service configuration.
        """
        return self.get_service(service_name)['Config']

    def get_constraints(self, service_name):
        return self.rpc(
            {"Type": "Client",
             "Request": "GetServiceConstraints",
             "Params": {
                 "ServiceName": service_name}})['Constraints']

    def set_constraints(self, service_name, constraints):
        return self.rpc(
            {"Type": "Client",
             "Request": "SetServiceConstraints",
             "Params": {
                 "ServiceName": service_name,
                 "Constraints": self._prepare_constraints(constraints)}})

    def update_service(self, service_name, charm_url="", force_charm_url=False,
                       min_units=None, settings=None, constraints=None):
        """Update a service.

        Can update a service's charm, modify configuration, constraints,
        and the minimum number of units.
        """
        svc_config = {}
        if settings:
            svc_config = self._prepare_strparams(settings)

        return self.rpc(
            {"Type": "Client",
             "Request": "ServiceUpdate",
             "Params": {
                 "ServiceName": service_name,
                 "CharmUrl": charm_url,
                 "MinUnits": min_units,
                 "SettingsStrings": svc_config,
                 "Constraints": self._prepare_constraints(constraints)}})

    def destroy_service(self, service_name):
        """Destroy a service and all of its units.

        On versions of juju 1.22+ this will also deallocate the iaas
        machine resources those units were assigned to if they
        were the only unit residing on the machine.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceDestroy",
            "Params": {
                "ServiceName": service_name}})

    def expose(self, service_name):
        """Provide external access to a given service.

        Will manipulate the iaas layer's firewall machinery
        to enabmle public access from outside of the environment.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceExpose",
            "Params": {
                "ServiceName": service_name}})

    def unexpose(self, service_name):
        """Remove external access to a given service.

        Will manipulate the iaas layer's firewall machinery
        to disable public access from outside of the environment.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceUnexpose",
            "Params": {
                "ServiceName": service_name}})

    def valid_relation_names(self, service_name):
        """All possible relation names of a service.

        Per its charm metadata.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "ServiceCharmRelations",
            "Params": {
                "ServiceName": service_name}})

    def add_relation(self, endpoint_a, endpoint_b):
        """Add a relation between two endpoints."""
        return self.rpc({
            'Type': 'Client',
            'Request': 'AddRelation',
            'Params': {
                'Endpoints': [endpoint_a, endpoint_b]
            }})

    def remove_relation(self, endpoint_a, endpoint_b):
        """Remove a relation between two endpoints."""
        return self.rpc({
            'Type': 'Client',
            'Request': 'DestroyRelation',
            'Params': {
                'Endpoints': [endpoint_a, endpoint_b]
            }})

    # Units
    def add_units(self, service_name, num_units=1):
        """Add n units of a given service.

        Machines will be allocated from the iaas provider
        or unused machines in the environment that
        match the service's constraints.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "AddServiceUnits",
            "Params": {
                "ServiceName": service_name,
                "NumUnits": num_units}})

    def add_unit(self, service_name, machine_spec=None):
        """Add a unit of the given service

        Optionally with placement onto a given existing
        machine or a new container.
        """
        params = {
            "ServiceName": service_name,
            "NumUnits": 1}
        if machine_spec:
            params["ToMachineSpec"] = machine_spec
        return self.rpc({
            "Type": "Client",
            "Request": "AddServiceUnits",
            "Params": params})

    def remove_units(self, unit_names):
        """Remove the given service units.
        """
        return self.rpc({
            "Type": "Client",
            "Request": "DestroyServiceUnits",
            "Params": {
                "UnitNames": unit_names}})


class EnvironmentManager(APIFacade):
    """Create multiple environments within a state server.

    ***Jan 2015 - Note MESS is still under heavy development
    and under a feature flag, api is likely not stable.***
    """
    key = "mess"
    name = "EnvironmentManager"
    versions = [1]

    def create(self, owner, account, config):
        """Create a new logical environment within a state server.
        """
        return self.rpc({
            'Request': 'CreateEnvironment',
            'Params': {'OwnerTag': self._format_user_tag(owner),
                       'Account': account,
                       'Config': config}})

    def list(self, owner):
        """List environments available to the given user.

        >>> env.mess.list('user-admin')
        {u'Environments': [
            {u'OwnerTag': u'user-admin@local',
             u'Name': u'ocean',
             u'UUID': u'f8947ad0-c592-48d9-86d1-d948ec90f6cd'}]}
        """
        return self.rpc({
            'Request': 'ListEnvironments',
            'Params': {'Tag': self._format_user_tag(owner)}})
