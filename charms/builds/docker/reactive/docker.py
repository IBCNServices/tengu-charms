#!/usr/bin/env python3
# pylint:disable=c0111,c0103
from subprocess import check_call, check_output, CalledProcessError

from charmhelpers.core import host, unitdata
from charmhelpers.core.hookenv import (
    config,
    status_set,
    open_port,
    log,
)
from charmhelpers.core.templating import render

from charms.reactive import remove_state, set_state, when, when_not

from charms import layer  # pylint:disable=E0611

from charms import apt  # pylint:disable=E0611,E1101

# 2 Major events are emitted from this layer.
#
# `docker.ready` is an event intended to signal other layers that need to
# plug into the plumbing to extend the docker daemon. Such as fire up a
# bootstrap docker daemon, or predependency fetch + dockeropt rendering
#
# `docker.available` means the docker daemon setup has settled and is prepared
# to run workloads. This is a broad state that has large implications should
# you decide to remove it. Production workloads can be lost if no restart flag
# is provided.

# Be sure you bind to it appropriately in your workload layer and
# react to the proper event.


@when_not('docker.ready', 'apt.installed.docker.io')
def install():
    layer_opts = layer.options('docker')
    if layer_opts['skip-install']:
        set_state('docker.available')
        set_state('docker.ready')
        return

    # Install docker-engine from apt.
    status_set(
        'maintenance',
        'Installing docker-engine via apt install docker.io.')
    apt.queue_install(['docker.io'])

    unitdata.kv().set('next_port', 30000)


@when('apt.installed.docker.io')
@when_not('docker.ready')
def configure_docker():
    reload_system_daemons()

    # Make with the adding of the users to the groups
    check_call(['usermod', '-aG', 'docker', 'ubuntu'])

    log('Docker installed, setting "docker.ready" state.')
    set_state('docker.ready')


@when('docker.ready')
@when_not('docker.available')
def signal_workloads_start():
    ''' Signal to higher layers the container runtime is ready to run
        workloads. At this time the only reasonable thing we can do
        is determine if the container runtime is active. '''

    # before we switch to active, probe the runtime to determine if
    # it is available for workloads. Assumine response from daemon
    # to be sufficient

    if not _probe_runtime_availability():
        status_set('waiting', 'Container runtime not available.')
        return

    status_set('active', 'Ready')
    set_state('docker.available')


@when('docker.restart')
def docker_restart():
    '''Other layers should be able to trigger a daemon restart. Invoke the
    method that recycles the docker daemon.'''
    recycle_daemon()
    remove_state('docker.restart')


@when('dockerhost.available')
def run_images(dh):
    images = dh.images
    log(images)
    for image in images:
        run_image(dh, image)


def recycle_daemon():
    '''Render the docker template files and restart the docker daemon on this
    system.'''
    log('Restarting docker service.')

    # Re-render our docker daemon template at this time... because we're
    # restarting. And its nice to play nice with others. Isn't that nice?
    render('docker.systemd', '/lib/systemd/system/docker.service', config())
    reload_system_daemons()
    host.service_restart('docker')

    if not _probe_runtime_availability():
        status_set('waiting', 'Container runtime not available.')
        return


def reload_system_daemons():
    ''' Reload the system daemons from on-disk configuration changes '''
    log('Reloading system daemons.')
    lsb = host.lsb_release()
    code = lsb['DISTRIB_CODENAME']
    if code != 'trusty':
        command = ['systemctl', 'daemon-reload']
        check_call(command)
    else:
        host.service_reload('docker')


def _probe_runtime_availability():
    ''' Determine if the workload daemon is active and responding '''
    try:
        cmd = ['docker', 'info']
        check_call(cmd)
        return True
    except CalledProcessError:
        # Remove the availability state if we fail reachability
        remove_state('docker.available')
        return False


def run_image(dh, image):
    '''When the provided image is not running, set it up and run it. '''
    log(image)
    container = get_container_id(image)
    if container:
        log(
            'There is already a container ({})\
             for this image.'.format(container))
        return

    log('Fetching image {}'.format(image['name']))
    if image['username'] and image['secret']:
        status_set(
            'maintenance',
            'Pulling docker image from private docker hub.')
        cmd = ['docker', 'login',
               '-u', image['username'],
               '-p', image['secret']]
        check_call(cmd)
    elif image['username']:
        status_set(
            'blocking',
            'Pulling the docker image failed. When providing a username, make \
            sure you also fill in the secret.')
        return
    elif image['secret']:
        status_set(
            'blocking',
            'Pulling the docker image failed. When providing a secret, make \
            sure you also fill in the username.')
        return

    cmd = ['docker', 'pull', image['image']]
    check_call(cmd)

    cmd = ['docker', 'run', '--name', '{}'.format(image['name'])]
    published_ports = {}
    if image['daemon']:
        cmd.append('-d')
    log(image['ports'])
    if image['interactive']:
        cmd.append('-i')
    if image['ports']:
        kv = unitdata.kv()
        next_port = kv.get('next_port')
        log(
            'For this docker engine, the next \
            available port is {}.'.format(next_port))
        for port in image['ports']:
            cmd.append('-p')
            next_port = next_port + 1
            cmd.append('{}:{}'.format(next_port, port.strip()))
            published_ports[port.strip()] = next_port
        kv.set('next_port', next_port)
        log(
            'Reset the next available port for \
            this docker engine to {}.'.format(next_port))
        dh.send_published_ports(published_ports)

    cmd.append('{}'.format(image['image']))
    log(cmd)
    check_call(cmd)
    for port in published_ports.values():
        open_port(port)


def get_container_id(image):
    cmd = ['docker', 'ps', '-aq', '-f', 'name={}'.format(image['name'])]
    return check_output(cmd).decode('utf-8').strip()


def remove_container(container_id):
    cmd = ['docker', 'rm', '-f', container_id]
    return check_call(cmd)
