import subprocess
import os
import tarfile

from charms.reactive import when, when_not, set_state
from charmhelpers.core import hookenv



@when_not('apache-nifi.installed')
@when('java.installed')
def install_apache_nifi():
    hookenv.log('Installing Apache NiFi')
    # Java -version commands output ends up in error stream, so parsing it to the
    # standard output stream is needed.
    java = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT)
    version = java.split('.')
    if 'Open' in java:
        java_home = '/usr/lib/jvm/java-1.%s.0-openjdk-amd64/' % version[1]
    else:
        java_home = '/usr/lib/jvm/java-%s-oracle' % version[1]
    add_line_to_file('JAVA_HOME="%s"' % java_home, '/etc/environment')
    add_line_to_file('export JAVA_HOME', '/etc/environment')
    subprocess.call('.', '/etc/environment')
    filesdir = '%s/files' % hookenv.charm_dir()
    # Next two lines are just for testing purposes
    print filesdir
    hookenv.log(filesdir)
    nifi = 'nifi-1.0.0'
    nifitar = tarfile.open('%s/%s-bin.tar.gz' % (filesdir, nifi))
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
