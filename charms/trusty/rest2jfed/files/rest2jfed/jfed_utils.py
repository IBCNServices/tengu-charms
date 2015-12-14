"""
Wrapper around jFed_CLI tool
See http://doc.ilabt.iminds.be/jfed-documentation/cli.html
"""
import subprocess
import os
# Own modules
from output import fail, warn, debug #pylint: disable=f0401


class JFed(object):
    """ Wrapper around jFed_CLI tool """
    def __init__(self,
                 _rspec_path,
                 _project_name,
                 _lib_location,
                 key_path=None,
                 password=None,
                 s4cert=None,
                 properties=None,
                 java_path='java'):
        self.rspec_path = _rspec_path
        self.key_path = key_path
        self.password = password
        self.lib_location = _lib_location
        self.project_name = _project_name
        self.s4cert = s4cert
        self.properties = properties
        self.java_path = java_path
        if self.rspec_path and not os.path.isfile(self.rspec_path):
            fail("Could not find rspec at %s" % self.rspec_path)
            exit(1)
        if self.key_path and not os.path.isfile(self.key_path):
            fail("Could not find key at %s" % self.key_path)
            exit(1)
        if self.properties and not os.path.isfile(self.properties):
            fail("Could not find properties at %s" % self.properties)
            exit(1)


    def sliver_status(self, slice_name):
        """Return status. Possible values:
            DOES_NOT_EXIST
            UNALLOCATED
            READY
            UNKNOWN"""
        status_c = ['status']
        output = self.run_command(status_c, slice_name, True)
        print output
        if "does not exist. Cannot continue." in output:
            return "DOES_NOT_EXIST"
        elif "has status UNALLOCATED" in output:
            return "UNALLOCATED"
        elif "has status READY" in output:
            return "READY"
        elif "UNKNOWN" in output:
            return "UNKNOWN"
        if "does not yet exist" in output:
            return "DOES_NOT_EXIST"
        else:
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
        output = self.run_command(create_c,
                                  slice_name,
                                  ignore_errors=True)
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
        output = self.run_command(delete_c, slice_name,
                                  ignore_errors=True)
        debug('output delete: {}'.format(output))
        return output


    def renew_slice(self, slice_name, exp_hours):
        """Renews the slice with given name so it has expiration time of x
            hours"""
        renew_c = ['renew', '--expiration-hours', str(exp_hours)]
        output = self.run_command(renew_c, slice_name,
                                  ignore_errors=True)
        debug('output renew: {}'.format(output))
        return output


    def get_userinfo(self):
        """ Returns info about user """
        command_c = ['userinfo']
        output = self.run_command(
            command_c, None, ignore_errors=True)
        debug('output userinfo: {}'.format(output))
        return output


    def get_sliceinfo(self, slice_name):
        """ Returns slice info"""
        command_c = ['slice-info']
        output = self.run_command(
            command_c, slice_name, ignore_errors=True)
        debug('output slice-info: {}'.format(output))
        return output


    def run_command(self,
                    command_c,
                    slice_name,
                    ignore_errors=False,
                    call_log=False):
        """ runs given command for slice name and returns output.
        command_c should be an array
        """
        # Required args
        experimenter_c = [self.java_path, '-jar',
                          self.lib_location + '/jfed_cli/experimenter-cli.jar']
        # Optional args
        # All optional args need to be initialized as array
        password_c = []
        key_c = []
        prop_c = []
        s4_c = []
        call_log_c = []
        rspec_c = []
        sliver_c = []
        if self.rspec_path:
            rspec_c = ['--rspec', self.rspec_path]
        if slice_name:
            sliver_c = ['-s', 'urn:publicid:IDN+wall2.ilabt.iminds.be:' +
                        self.project_name + '+slice+' + slice_name]
        if call_log:
            call_log_c = ['--call-log', '/var/log/jfed_call_log']
        if self.key_path:
            key_c = ['-p', self.key_path]
            if self.password:
                password_c = ['-P', self.password]

        elif self.properties:
            prop_c = ['--context-file', self.properties]
        else:
            fail("either keyfile or context file must be specified")
        if self.s4cert:
            s4_c = ['--speaks-for', self.s4cert]
        # Create command
        command = experimenter_c + \
                  command_c + \
                  sliver_c + \
                  rspec_c + \
                  key_c + \
                  password_c + \
                  s4_c + \
                  prop_c + \
                  call_log_c
        debug("command is: `{}`".format(' '.join(command)))
        try:
            return subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            if ignore_errors:
                return ex.output
            print ex.output
            raise


    def exp_exists(self, experiment_name):
        """Checks if jFed experiment with given name exists.
        If so, returns status"""
        status = self.sliver_status(experiment_name)
        if status not in ('DOES_NOT_EXIST', 'UNALLOCATED'):
            return status
        return False
