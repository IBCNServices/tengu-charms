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

import re
import time
import yaml
import socket
from contextlib import contextmanager
from subprocess import check_call, check_output, CalledProcessError
from xml.etree import ElementTree as ET
from xml.dom import minidom
from distutils.util import strtobool as _strtobool
from path import Path
from tempfile import NamedTemporaryFile

from charmhelpers.core import unitdata
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers import fetch


class DistConfig(object):
    """
    This class processes distribution-specific configuration options.

    Some configuration options are specific to the Hadoop distribution,
    (e.g. Apache, Hortonworks, MapR, etc). These options are immutable and
    must not change throughout the charm deployment lifecycle.

    Helper methods are provided for keys that require action. Presently, this
    includes adding/removing directories, dependent packages, and groups/users.
    Other required keys may be listed when instantiating this class, but this
    will only validate these keys exist in the yaml; it will not provide any
    helper functionality for unkown keys.

    :param str filename: File to process (default dist.yaml)
    :param list required_keys: A list of keys required to be present in the yaml

    Example dist.yaml with supported keys:
        vendor: '<name>'
        hadoop_version: '<version>'
        packages:
            - '<package 1>'
            - '<package 2>'
        groups:
            - '<name>'
        users:
            <user 1>:
                groups: ['<primary>', '<group>', '<group>']
            <user 2>:
                groups: ['<primary>']
        dirs:
            <dir 1>:
                path: '</path/to/dir>'
                perms: 0777
            <dir 2>:
                path: '{config[<option>]}'  # value comes from config option
                owner: '<user>'
                group: '<group>'
                perms: 0755
        ports:
            <name1>:
                port: <port>
                exposed_on: <service>  # optional
            <name2>:
                port: <port>
                exposed_on: <service>  # optional
    """
    def __init__(self, filename='dist.yaml', required_keys=None):
        self.yaml_file = filename
        self.dist_config = yaml.load(Path(self.yaml_file).text())

        # validate dist.yaml
        missing_keys = set(required_keys or []) - set(self.dist_config.keys())
        if missing_keys:
            raise ValueError('{} is missing required option{}: {}'.format(
                filename,
                's' if len(missing_keys) > 1 else '',
                ', '.join(missing_keys)))

        for opt in required_keys:
            setattr(self, opt, self.dist_config[opt])

    def path(self, key):
        config = hookenv.config()
        dirs = {name: self.dirs[name]['path'] for name in self.dirs.keys()}
        levels = 0
        old_path = None
        path = self.dirs[key]['path']
        while '{' in path and path != old_path:
            levels += 1
            if levels > 100:
                raise ValueError('Maximum level of nested dirs references exceeded for: {}'.format(key))
            old_path = path
            path = path.format(config=config, dirs=dirs)
        return Path(path)

    def port(self, key):
        return self.ports.get(key, {}).get('port')

    def exposed_ports(self, service):
        exposed = []
        for port in self.ports.values():
            if port.get('exposed_on') == service:
                exposed.append(port['port'])
        return exposed

    def add_dirs(self):
        for name, details in self.dirs.items():
            host.mkdir(
                self.path(name),
                owner=details.get('owner', 'root'),
                group=details.get('group', 'root'),
                perms=details.get('perms', 0o755))

    def add_packages(self):
        with disable_firewall():
            fetch.apt_update()
            fetch.apt_install(self.packages)

    def add_users(self):
        for group in self.groups:
            host.add_group(group)
        for username, details in self.users.items():
            primary_group = None
            groups = details.get('groups', [])
            if groups:
                primary_group = groups[0]
            host.adduser(username, group=primary_group)
            for group in groups:
                host.add_user_to_group(username, group)

    def remove_dirs(self):
        # TODO: no removal function exists in CH, just log what we would do.
        for name in self.dirs.items():
            hookenv.log('noop: remove directory {0}'.format(name))

    def remove_packages(self):
        # TODO: no removal function exists in CH, just log what we would do.
        for name in self.packages.items():
            hookenv.log('noop: remove package {0}'.format(name))

    def remove_users(self):
        # TODO: no removal function exists in CH, just log what we would do.
        for user in self.users.items():
            hookenv.log('noop: remove user {0}'.format(user))
        for group in self.groups:
            hookenv.log('noop: remove group {0}'.format(group))


@contextmanager
def disable_firewall():
    """
    Temporarily disable the firewall, via ufw.
    """
    status = check_output(['ufw', 'status'])
    already_disabled = 'inactive' in status
    if not already_disabled:
        check_call(['ufw', 'disable'])
    try:
        yield
    finally:
        if not already_disabled:
            check_call(['ufw', 'enable'])


def re_edit_in_place(filename, subs):
    """
    Perform a set of in-place edits to a file.

    :param str filename: Name of file to edit
    :param dict subs: Mapping of patterns to replacement strings
    """
    with Path(filename).in_place() as (reader, writer):
        for line in reader:
            for pat, repl in subs.iteritems():
                line = re.sub(pat, repl, line)
            writer.write(line)


@contextmanager
def xmlpropmap_edit_in_place(filename):
    """
    Edit an XML property map (configuration) file in-place.

    This helper acts as a context manager which edits an XML file of the form:

        <configuration>
            <property>
                <name>property-name</name>
                <value>property-value</value>
                <description>Optional property description</description>
            </property>
            ...
        </configuration>

    This context manager yields a dict containing the existing name/value
    mappings.  Properties can then be modified, added, or removed, and the
    changes will be reflected in the file.

    Example usage:

        with xmlpropmap_edit_in_place('my.xml') as props:
            props['foo'] = 'bar'
            del props['removed']

    Note that the file is not locked during the edits.
    """
    tree = ET.parse(filename)
    root = tree.getroot()
    props = {}
    for prop in root.findall('property'):
        props[prop.find('name').text] = prop.find('value').text
    old_props = set(props.keys())
    yield props
    new_props = set(props.keys())
    added = new_props - old_props
    modified = new_props & old_props
    removed = old_props - new_props
    for prop in root.findall('property'):
        name = prop.find('name').text
        if name in modified and props[name] is not None:
            prop.find('value').text = str(props[name])
        elif name in removed:
            root.remove(prop)
    for name in added:
        prop = ET.SubElement(root, 'property')
        ET.SubElement(prop, 'name').text = name
        ET.SubElement(prop, 'value').text = str(props[name])
    for node in tree.iter():
        node.tail = None
        node.text = (node.text or '').strip() or None
    prettied = minidom.parseString(ET.tostring(root)).toprettyxml(indent='    ')
    Path(filename).write_text(prettied)


@contextmanager
def environment_edit_in_place(filename='/etc/environment'):
    """
    Edit the `/etc/environment` file in-place.

    There is no standard definition for the format of `/etc/environment`,
    but the convention, which this helper supports, is simple key-value
    pairs, separated by `=`, with optionally quoted values.

    Note that this helper will implicitly quote all values.

    Also note that the file is not locked during the edits.
    """
    etc_env = Path(filename)
    lines = [l.strip().split('=') for l in etc_env.lines()]
    data = {k.strip(): v.strip(' \'"') for k, v in lines}
    yield data
    etc_env.write_lines('{}="{}"'.format(k, v) for k, v in data.items())


def strtobool(value):
    return bool(_strtobool(str(value)))


def normalize_strbool(value):
    intbool = strtobool(value)
    return str(bool(intbool)).lower()


def jps(name):
    """
    Get PIDs for named Java processes, for any user.
    """
    pat = re.sub(r'^(.)', r'^[^ ]*java .*[\1]', name)
    try:
        output = check_output(['sudo', 'pgrep', '-f', pat])
    except CalledProcessError:
        return []
    return filter(None, map(str.strip, output.split('\n')))


class TimeoutError(Exception):
    pass


def read_etc_env():
    """
    Read /etc/environment and return it as a dict.
    """
    etc_env = Path('/etc/environment')
    env = {}
    if etc_env.exists():
        for line in etc_env.lines():
            var, value = line.split('=')
            env[var.strip()] = value.strip().strip('"')
    return env


def run_as(user, command, *args, **kwargs):
    """
    Run a command as a particular user, using ``/etc/environment`` and optionally
    capturing and returning the output.

    Raises subprocess.CalledProcessError if command fails.

    :param str user: Username to run command as
    :param str command: Command to run
    :param list args: Additional args to pass to command
    :param dict env: Additional env variables (will be merged with ``/etc/environment``)
    :param bool capture_output: Capture and return output (default: False)
    :param str input: Stdin for command
    """
    parts = [command] + list(args)
    quoted = ' '.join("'%s'" % p for p in parts)
    env = read_etc_env()
    if 'env' in kwargs:
        env.update(kwargs['env'])
    run = check_output if kwargs.get('capture_output') else check_call
    try:
        stdin = None
        if 'input' in kwargs:
            stdin = NamedTemporaryFile()
            stdin.write(kwargs['input'])
            stdin.seek(0)
        return run(['su', user, '-c', quoted], env=env, stdin=stdin)
    finally:
        if stdin:
            stdin.close()  # this also removes tempfile


def update_etc_hosts(ips_to_names):
    '''
    Update /etc/hosts given a mapping of managed IP / hostname pairs.

    :param dict ips_to_names: mapping of IPs to hostnames (must be one-to-one)
    '''
    etc_hosts = Path('/etc/hosts')
    hosts_contents = etc_hosts.lines()
    comment_pat = re.compile(r'^\s*#?\s*([^#]*)\s*#.*$')
    IP_pat = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

    new_lines = []
    managed = {}
    for line in hosts_contents:
        if '# JUJU MANAGED' not in line:
            # pass-thru unmanaged lines unchanged
            new_lines.append(line)
        else:
            # record existing managed entries
            # managed is inverted (name-to-ip) because, while it's ok to have
            # multiple hosts resolve to the same IP, having multiple IPs for
            # the same host can be problematic
            ip, name = comment_pat.sub(r'\1', line).split(None, 2)
            managed[name] = ip
    # add or update new hosts
    managed.update({name: ip for ip, name in ips_to_names.items()})

    # render all of our managed entries as lines
    for name, ip in managed.items():
        line = '%s %s  # JUJU MANAGED' % (ip, name)
        if not IP_pat.match(ip):
            line = '# %s (INVALID IP)' % line
        # add new host
        new_lines.append(line)

    # write new /etc/hosts
    etc_hosts.write_lines(new_lines, append=False)


def manage_etc_hosts():
    """
    Manage the /etc/hosts file from the host entries stored in unitdata.kv()
    by the various relations.
    """
    kv_hosts = get_kv_hosts()
    hookenv.log('Updating /etc/hosts from kv with %s' %
                kv_hosts, hookenv.DEBUG)
    update_etc_hosts(kv_hosts)


def resolve_private_address(addr):
    IP_pat = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    contains_IP_pat = re.compile(r'\d{1,3}[-.]\d{1,3}[-.]\d{1,3}[-.]\d{1,3}')
    if IP_pat.match(addr):
        return addr  # already IP
    try:
        ip = socket.gethostbyname(addr)
        return ip
    except socket.error as e:
        hookenv.log('Unable to resolve private IP: %s (will attempt to guess)' % addr, hookenv.ERROR)
        hookenv.log('%s' % e, hookenv.ERROR)
        contained = contains_IP_pat.search(addr)
        if not contained:
            raise ValueError('Unable to resolve or guess IP from private-address: %s' % addr)
        return contained.groups(0).replace('-', '.')


def initialize_kv_host():
    # get the hostname attrs from our local unit and update the kv store
    local_ip = hookenv.unit_private_ip()
    local_host = hookenv.local_unit().replace('/', '-')
    update_kv_host(local_ip, local_host)


def get_kv_hosts():
    return unitdata.kv().getrange('etc_host.', strip=True)


def update_kv_host(ip, host):
    unit_kv = unitdata.kv()

    # store attrs in the kv as 'etc_host.<ip>'; kv.update will insert
    # a new record or update any existing key with current data.
    unit_kv.update({ip: host},
                   prefix="etc_host.")
    unit_kv.flush(True)


def get_ssh_key(user):
    sshdir = Path('/home/%s/.ssh' % user)
    if not sshdir.exists():
        host.mkdir(sshdir, owner=user, group='hadoop', perms=0o755)
    keyfile = sshdir / 'id_rsa'
    pubfile = sshdir / 'id_rsa.pub'
    authfile = sshdir / 'authorized_keys'
    if not pubfile.exists():
        (sshdir / 'config').write_lines([
            'Host *',
            '    StrictHostKeyChecking no'
        ], append=True)
        check_call(['ssh-keygen', '-t', 'rsa', '-P', '', '-f', keyfile])
        host.chownr(sshdir, user, 'hadoop')
    # allow ssh'ing to localhost; useful for things like start_dfs.sh
    if not authfile.exists():
        Path.copy(pubfile, authfile)
    return pubfile.text()


def install_ssh_key(user, ssh_key):
    sshdir = Path('/home/%s/.ssh' % user)
    if not sshdir.exists():
        host.mkdir(sshdir, owner=user, group='hadoop', perms=0o755)
    Path(sshdir / 'authorized_keys').write_text(ssh_key, append=True)
    host.chownr(sshdir, user, 'hadoop')


def wait_for_hdfs(timeout):
    start = time.time()
    while time.time() - start < timeout:
        try:
            output = run_as('hdfs', 'hdfs', 'dfsadmin', '-report', capture_output=True)
            if 'Datanodes available' in output or 'Live datanodes' in output:
                return True
        except CalledProcessError as e:
            output = e.output  # probably a "connection refused"; wait and try again
        time.sleep(2)
    raise TimeoutError('Timed-out waiting for HDFS:\n%s' % output)


def wait_for_jps(process_name, timeout):
    hookenv.log('Waiting for jps to see %s' % process_name, hookenv.DEBUG)
    start = time.time()
    while time.time() - start < timeout:
        if jps(process_name):
            hookenv.log('Jps shows %s is running' % process_name, hookenv.DEBUG)
            return True
        time.sleep(2)
    raise TimeoutError('Timed-out waiting for jps process:\n%s' % process_name)


class verify_resources(object):
    """
    Predicate for specific named resources, with useful rendering in the logs.

    :param str *which: One or more resource names to fetch & verify.  Defaults to
        all non-optional resources.
    """
    def __init__(self, *which):
        self.which = list(which)

    def __str__(self):
        return '<resources %s>' % ', '.join(map(repr, self.which))

    def __call__(self):
        import jujuresources
        result = True
        if not jujuresources.verify(self.which):
            mirror_url = hookenv.config('resources_mirror')
            hookenv.status_set('maintenance', 'Fetching resources')
            result = jujuresources.fetch(self.which, mirror_url=mirror_url)
            if not result:
                missing = jujuresources.invalid(self.which)
                hookenv.status_set('blocked', 'Unable to fetch required resource%s: %s' % (
                    's' if len(missing) > 1 else '',
                    ', '.join(missing),
                ))
        return result
