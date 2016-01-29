#pylint:disable=C0325
"""
Wrapper around jFed_CLI tool
See http://doc.ilabt.iminds.be/jfed-documentation/cli.html
"""
import subprocess
import os
import json
import re


#Pip dependencies
import yaml

# Own modules
from output import fail, warn, debug


class JFed(object):
    """ Wrapper around jFed_CLI tool """
    def __init__(self,
                 _project_name,
                 key_path=None,
                 password=None,
                 s4cert=None,
                 properties=None):
        self.key_path = key_path
        self.password = password
        self.project_name = _project_name
        self.s4cert = s4cert
        self.properties = properties

        # Get java path from JAVA_HOME environment variable. If environment var
        # is unset, use 'java' and hope java is included in path.
        java_home = os.environ.get('JAVA_HOME')
        if java_home:
            self.java_path = '{}/bin/java'.format(java_home)
        else:
            self.java_path = 'java'
        # Get jfed_cli path from JFED_CLI environment variable. If environment
        # var is unset, use 'jfed_cli' and hope jfed_cli is included in path.
        self.jfed_cli_path = os.environ.get('JFED_CLI', 'jfed_cli')
        # Boolean that tells us if we should write call_log
        self.call_log = os.environ.get('JFED_CALL_LOG')


    def sliver_status(self, slice_name, extended=False):
        """Return status. Possible values:
            DOES_NOT_EXIST
            UNALLOCATED
            READY
            UNKNOWN
            FAIL"""
        status_c = ['status']
        output = self.run_command(status_c, slice_name=slice_name)
        print output
        if "does not exist. Cannot continue." in output:
            return "DOES_NOT_EXIST"
        elif "already exists" in output:
            try:
                output = output[output.index('{'):]
                outputdict = yaml.load(output)
                if extended:
                    return json.dumps(outputdict)
                else:
                    return outputdict['AMs'].values()[0]['amGlobalSliverStatus']
            except (yaml.parser.ParserError, ValueError) as exc:
                print("could not parse status from ouptut. output: " + output)
                raise exc
        else:
            print("slice status unknown. Output: \n %s" % output)
            raise Exception("slice status unknown. Output: \n %s" % output)


    def create_slice(self, slice_name, manifestpath, exp_hours=168):
        """Create new slice with given slice_name. Creates manifest on succes
           and returns status. Status can be one of the following:
           - SUCCESS
           - FAIL_NO_BANDWITH
           - FAIL_NO_NODES
           - FAIL_NOT_YOUR_CREDENTIAL
           - FAIL_UNKNOWN"""
        debug("creating slice {} and waiting untill all nodes are ready."
              "This can take a few minutes.".format(slice_name))
        create_c = ['create', '--create-slice',
                    # do not include userkeys because
                    # this doesn't work with "speaks-for"
                    '--ssh-keys', 'usercert,rspec',
                    '--manifest', manifestpath,
                    '--expiration-hours', str(exp_hours),
                    '--rewrite-rspec']
        output = self.run_command(create_c, slice_name=slice_name)
        if "The sliver is ready." in output:
            assert os.path.isfile(manifestpath)
            return "SUCCESS"
        elif "Not enough bandwidth to connect some nodes" in output:
            return "FAIL_NO_BANDWITH"
        elif "Not enough nodes" in output:
            return "FAIL_NO_NODES"
        elif "This is not your credential" in output:
            return "FAIL_NOT_YOUR_CREDENTIAL"
        else:
            warn("unknown state in: {}".format(output))
            return "FAIL_UNKNOWN: " + output


    def delete_slice(self, slice_name):
        """Deletes slice with given name"""
        delete_c = ['delete']
        output = self.run_command(delete_c, slice_name=slice_name)
        debug('output delete: {}'.format(output))
        return output


    def renew_slice(self, slice_name, exp_hours):
        """Renews the slice with given name so it has expiration time of x
            hours"""
        renew_c = ['renew', '--expiration-hours', str(exp_hours)]
        output = self.run_command(renew_c, slice_name=slice_name)
        debug('output renew: {}'.format(output))
        return output


    def get_userinfo(self):
        """ Returns info about user """
        command_c = ['userinfo']
        output = self.run_command(command_c)
        debug('output userinfo: {}'.format(output))
        return output


    def get_sliceinfo(self, slice_name):
        """ Returns slice info"""
        command_c = ['slice-info']
        output = self.run_command(command_c, slice_name=slice_name)
        debug('output slice-info: {}'.format(output))
        return output


    def run_command(self,
                    command_c,
                    slice_name=None,
                    rspec_path=None):
        """ runs given command for slice name and returns output.
        command_c should be an array
        """
        # Required args
        command = [self.java_path, '-jar', self.jfed_cli_path]
        command += command_c
        # Optional args
        # All optional args need to be initialized as array
        if rspec_path:
            command += ['--rspec', rspec_path]
        if slice_name:
            slice_name = 'urn:publicid:IDN+wall2.ilabt.iminds.be:' + self.project_name + '+slice+' + slice_name
            command += ['-s', slice_name]
        if self.call_log:
            command += ['--call-log', '/var/log/jfed_call_log']
        if self.key_path:
            command += ['-p', self.key_path]
            if self.password:
                command += ['-P', self.password]
        elif self.properties:
            command += ['--context-file', self.properties]
        else:
            fail("either keyfile or context file must be specified")
        if self.s4cert:
            command += ['--speaks-for', self.s4cert]
        debug("command is: `{}`".format(' '.join(command)))
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            iserror = True
        return parse_output(output, iserror)


    def exp_exists(self, experiment_name):
        """Checks if jFed experiment with given name exists.
        If so, returns status"""
        status = self.sliver_status(experiment_name)
        if status not in ('DOES_NOT_EXIST', 'UNALLOCATED'):
            return status
        return False


def parse_output(output, iserror):
    """ Parses output of jfed_cli tool and returns result as dict """
    s4re = '^Using speaksFor credential for user "([^"]*)".*\n'
    match = re.match(s4re, output)
    if match:
        s4cred = match.group(1)
        output = re.sub(s4re, '', output, 1)
    msgre = '([^:^\n]+): '
    match = re.match(msgre, output)
    if match:
        msg = match.group(1).lstrip()
        output = re.sub(msgre, '', output, 1)
    else:
        raise Exception('Cannot interpret output: {}'.format(output))
    try:
        output = output.lstrip('"').rstrip().rstrip('"')
        odict = json.loads(output)
    except ValueError:
        raise Exception('Cannot convert output to json: {}'.format(output))
    return {
        'iserror': iserror,
        's4cred': s4cred,
        msg: odict,
    }
