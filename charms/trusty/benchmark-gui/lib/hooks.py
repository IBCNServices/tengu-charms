import json
import re
import os
import sys
import shutil
import logging
import subprocess

import requests

sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers.core import (
    hookenv,
    host,
    unitdata,
)

from charmhelpers import fetch
from helpers import apache2
from helpers.host import touch, extract_tar


def install():
    hookenv.status_set('maintenance', 'Installing CABS')
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages([
        'graphite-carbon',
        'graphite-web',
        'apache2',
        'apache2-mpm-worker',
        'libapache2-mod-wsgi',
        'postgresql',
        'python-virtualenv',
        'python-dev',
        'python-requests',
    ]))

    touch('/etc/apache2/sites-available/cabs-graphite.conf')
    shutil.copyfile('files/graphite.conf',
                    '/etc/apache2/sites-available/cabs-graphite.conf')
    shutil.copyfile('files/graphite-carbon', '/etc/default/graphite-carbon')
    apache2.enable_site('cabs-graphite')

    host.chownr('/var/lib/graphite', '_graphite', '_graphite')
    subprocess.check_call('sudo -u _graphite graphite-manage syncdb --noinput',
                          shell=True)

    extract_tar('payload/collector-web.tar.gz', '/opt/collector-web')
    config = hookenv.config()
    try:
        env = None
        if config.get('proxy'):
            env = dict(os.environ)
            env.update({'http_proxy': config.get('proxy'),
                        'https_proxy': config.get('proxy')})
        subprocess.check_call(['make', '.venv'], cwd='/opt/collector-web',
                              env=env)
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        hookenv.status_set(
            'blocked', 'Failed to create venv - do you require a proxy?')
        return

    # setup postgres for collector-web
    subprocess.check_call(['scripts/ensure_db_user.sh'])
    subprocess.check_call(['scripts/ensure_db.sh'])

    # Install upstart config for collector-web
    shutil.copyfile('/opt/collector-web/conf/upstart/collectorweb.conf',
                    '/etc/init/collectorweb.conf')

    host.chownr('/opt/collector-web', 'ubuntu', 'ubuntu')

    host.service_restart('apache2')
    host.service_restart('carbon-cache')
    host.service_restart('collectorweb')

    # Install cron, vhost for gui, etc
    hookenv.open_port(9000)
    hookenv.open_port(9001)
    hookenv.open_port(2003)


def configure(force=False):
    config = hookenv.config()

    def changed(key):
        return force or config.changed(key)

    if config.changed('proxy') and config.get('proxy'):
        shutil.rmtree('/opt/collector-web')
        install()
        if hookenv.status_get() == 'blocked':
            return  # We're blocked again

    with open('/etc/graphite/local_settings.py', 'r+') as f:
        contents = f.read()
        contents = re.sub(r'#TIME_ZONE = .*', "TIME_ZONE = 'Etc/UTC'",
                          contents)
        f.seek(0, 0)
        f.truncate()
        f.write(contents)

    if 'juju-secret' not in config:
        return

    ini_path = '/opt/collector-web/production.ini'
    with open(ini_path, 'r') as f:
        ini = f.read()

    api_addresses = os.getenv('JUJU_API_ADDRESSES')
    if api_addresses:
        juju_api = 'wss://%s' % api_addresses.split()[0]
        ini = re.sub(r'juju.api.endpoint =.*',
                     'juju.api.endpoint = %s' % juju_api, ini)

    ini = re.sub(
        r'graphite.url =.*',
        'graphite.url = http://%s:9001' % hookenv.unit_get('public-address'),
        ini)

    if changed('juju-user'):
        ini = re.sub(
            r'juju.api.user =.*',
            'juju.api.user = %s' % config.get('juju-user') or '', ini)

    if changed('juju-secret'):
        ini = re.sub(
            r'juju.api.secret =.*',
            'juju.api.secret = %s' % config.get('juju-secret') or '', ini)

    if changed('publish-url'):
        ini = re.sub(
            r'publish.url =.*',
            'publish.url = %s' % config.get('publish-url') or '', ini)

    with open(ini_path, 'w') as f:
        f.write(ini)

    host.service_restart('collectorweb')
    hookenv.status_set('active',
                       'Ready http://%s:9000' % hookenv.unit_public_ip())


def set_action_id(action_id):
    if unitdata.kv().get('action_id') == action_id:
        # We've already seen this action_id
        return

    unitdata.kv().set('action_id', action_id)

    if not action_id:
        return

    # Broadcast action_id to collectors
    for rid in hookenv.relation_ids('collector'):
        hookenv.relation_set(relation_id=rid, relation_settings={
            'action_id': action_id
        })


def benchmark():
    if not hookenv.in_relation_hook():
        return

    set_action_id(hookenv.relation_get('action_id'))

    benchmarks = hookenv.relation_get('benchmarks')
    if benchmarks:
        hookenv.log('benchmarks received: %s' % benchmarks)
        service = hookenv.remote_unit().split('/')[0]
        payload = {'benchmarks': [b for b in benchmarks.split(',')]}
        requests.post(
            'http://localhost:9000/api/services/{}'.format(service),
            data=json.dumps(payload),
            headers={
                'content-type': 'application/json'
            }
        )

    graphite_url = 'http://%s:9001' % hookenv.unit_get('public-address')

    hookenv.relation_set(hostname=hookenv.unit_private_ip(),
                         port=2003, graphite_port=9001,
                         graphite_endpoint=graphite_url, api_port=9000)


def emitter_rel():
    if hookenv.in_relation_hook():
        hookenv.relation_set(hostname=hookenv.unit_private_ip(), port=2003,
                             api_port=9000)


def start():
    host.service_reload('apache2')
    host.service_restart('collectorweb')


def stop():
    apache2.disable_site('cabs-graphite')
    os.remove('/etc/apache2/sites-available/cabs-graphite.conf')
    host.service_reload('apache2')
    host.service_stop('carbon-cache')
    host.service_stop('collectorweb')
