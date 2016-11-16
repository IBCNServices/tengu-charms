import subprocess
import os
import tarfile

from charms.reactive import when, when_not, set_state
from charmhelpers.core.hookenv import charm_dir


@when_not('apache-nifi.installed', 'java.unavailable')
def install_apache_nifi():
    java = subprocess.check_output('java', '-version')
    version = java.split('.')
    if 'Open' in java:
        java_home = '/usr/lib/jvm/java-1.%s.0-openjdk-amd64/' % version[1]
    else:
        java_home = '/usr/lib/jvm/java-%s-oracle' % version[1]
    add_line_to_file('JAVA_HOME="%s"' % java_home, '/etc/environment')
    add_line_to_file('export JAVA_HOME', 'etc/environment')
    subprocess.call('.', '/etc/environment')
    filesdir = '%s/files/' % charm_dir()
    nifi = 'nifi-1.0.0-bin.tar.gz'
    nifitar = tarfile.open('%s%s' % (filesdir, nifi))
    nifitar.extractall(filesdir)
    # add config variables in template, location is filesdir/confs
    subprocess.check_output('sh', '%s/bin/nifi.sh' % filesdir, 'install')

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
                print("line already present")
                found = True
    if not found:
        myfile = open(filepath, 'a+')
        myfile.write(line+"\n")
        myfile.close()
