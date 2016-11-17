import subprocess
import os
import tarfile

from charms.reactive import when, when_not, set_state
from charmhelpers.core import hookenv


@when_not('apache-nifi.installed')
@when('java.installed')
def install_apache_nifi():
    hookenv.log('Installing Apache NiFi')
    conf = hookenv.config()
    # shell=True is necessairy for the echo-command to access environment variables.
    # Since command is not user input, it is safe.
    java = subprocess.check_output('echo $JAVA_HOME', shell=True)
    if java == '':
        if conf['java-flavor'] == 'oracle':
            java_home = '/usr/lib/jvm/java-%s-oracle' % conf['java-major']
        else:
            java_home = '/usr/lib/jvm/java-1.%s.0-openjdk-amd64/' % conf['java-major']
        add_line_to_file('JAVA_HOME="%s"' % java_home, '/etc/environment')
        add_line_to_file('export JAVA_HOME', '/etc/environment')
        subprocess.call('.', '/etc/environment')
    filesdir = '%s/files' % hookenv.charm_dir()
    # Next line is just for testing purposes
    hookenv.log(filesdir)
    nifi = 'nifi-1.0.0'
    nifitar = tarfile.open('%s/%s-bin.tar.gz' % (filesdir, nifi))
    nifitar.extractall(filesdir)
    # ToDo: add config variables in template, location is filesdir/confs
    hookenv.log(subprocess.check_output('sh %s/bin/nifi.sh install %s' % (filesdir, conf['nifi-service-name'])))
    set_state('apache-nifi.installed')


# Source: https://github.com/mhmoerma/tengu-charms/blob/master/charms/layers/java/lib/oracle.py
def add_line_to_file(line, filepath):
    """appends line to file if not present"""
    filepath = os.path.realpath(filepath)
    if not os.path.isdir(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    found = False
    if os.path.isfile(filepath):
        with open(filepath, 'r+') as myfile:
            lst = myfile.readlines()
        for existingline in lst:
            if line in existingline:
                found = True
    if not found:
        myfile = open(filepath, 'a+')
        myfile.write(line+"\n")
        myfile.close()
