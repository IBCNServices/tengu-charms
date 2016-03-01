#pylint:disable=C0325,c0301
"""
Wrapper around jFed_CLI tool
See http://doc.ilabt.iminds.be/jfed-documentation/cli.html
"""
import subprocess
import os
import json
import re


#Pip dependencies

# Own modules
from output import fail, debug


class JfedError(Exception):
    """ Errors thrown by Jfed """
    def __init__(self, message, odict):
        # Call the base class constructor with the parameters it needs
        super(JfedError, self).__init__(message)
        # Add output dictionary variable
        self.odict = odict

class NotExistError(JfedError):
    """ Error thrown when requested resource doesn't exist """
    pass


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
        self.check_vars()


    def check_vars(self):
        """ Checks if all the variables of the class instance are good; if files exist and such. """
        paths = [
            self.java_path,
            self.jfed_cli_path,
        ]
        for var in paths:
            if not os.path.isfile(var):
                raise ValueError('file {} does not exist'.format(var))


    def get_userinfo(self):
        """ Returns info about user """
        command_c = ['userinfo']
        odict = self.run_command(command_c)
        return odict


    def get_sliceinfo(self, slice_name):
        """ Returns slice info"""
        command_c = ['slice-info']
        odict = self.run_command(command_c, slice_name=slice_name)
        return odict


    def get_slice_status(self, slice_name, rspec_path):
        """Return status of sliver DOES_NOT_EXIST
            UNALLOCATED
            READY
            UNKNOWN
            FAIL"""
        status_c = ['status']
        odict = self.run_command(status_c, slice_name=slice_name, rspec_path=rspec_path)
        if odict['existsbefore'] == False:
            status = 'DOES_NOT_EXIST'
        else:
            value = odict['json_output']['AMs'].itervalues().next()
            status = value['amGlobalSliverStatus']
        odict['short_status'] = status
        return odict


    def get_slice_expiration(self, slice_name, rspec_path):
        """ Get earliest sliver expiration date. Throws NotExistError """
        odict = self.get_slice_status(slice_name, rspec_path)
        if odict['short_status'] in ('DOES_NOT_EXIST', 'UNALLOCATED'):
            raise NotExistError("slice doesn't exist", odict)
        else:
            return odict['json_output']['earliestSliverExpireDate']


    def create_slice(self, slice_name, rspec_path, manifestpath, exp_hours=168):
        """Create new slice with given slice_name. Creates manifest on succes
           and returns status. Status can be one of the following:
           - SUCCESS
           - FAIL_NO_BANDWITH
           - FAIL_NO_NODES
           - FAIL_NOT_YOUR_CREDENTIAL
           - FAIL_UNKNOWN"""
        debug("creating slice {} and waiting until all nodes are ready."
              "This can take a few minutes.".format(slice_name))
        create_c = ['create', '--create-slice',
                    # do not include userkeys because
                    # this doesn't work with "speaks-for"
                    '--ssh-keys', 'usercert,rspec',
                    '--manifest', manifestpath,
                    '--expiration-hours', str(exp_hours),
                    '--rewrite-rspec']
        odict = self.run_command(create_c, slice_name=slice_name, rspec_path=rspec_path)
        sliver_available = odict.get('sliver_available', False)
        manifest_exists = os.path.isfile(manifestpath)
        exit_err = odict['is_exit_code_error']
        if exit_err or not manifest_exists or not sliver_available:
            raise JfedError('Create failed', odict)
        return odict


    def delete_slice(self, slice_name, rspec_path):
        """Deletes slice with given name"""
        delete_c = ['delete']
        odict = self.run_command(delete_c, slice_name=slice_name, rspec_path=rspec_path)
        exit_err = odict['is_exit_code_error']
        if exit_err:
            raise JfedError('Delete failed', odict)
        return odict


    def renew_slice(self, slice_name, rspec_path, exp_hours):
        """Renews the slice with given name so it has expiration time of x
            hours"""
        renew_c = ['renew', '--expiration-hours', str(exp_hours)]
        odict = self.run_command(renew_c, slice_name=slice_name, rspec_path=rspec_path)
        exit_err = odict['is_exit_code_error']
        req_renews = odict.get('requested_sliver_renews', 0)
        successfull_renews = odict.get('successfull_sliver_renews', -1)
        if exit_err or req_renews != successfull_renews:
            raise JfedError('Renew failed', odict)
        return odict


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
        iserror = False
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            output = ex.output
            iserror = True
        print "DEBUG: output = {}".format(output)
        return parse_output(output, iserror)


    def slice_exists(self, experiment_name, rspec):
        """Checks if jFed experiment with given name exists.
        If so, returns status"""
        status = self.get_slice_status(experiment_name, rspec)['short_status']
        if status in ('DOES_NOT_EXIST', 'UNALLOCATED'):
            return False
        return True


def parse_output(output, is_exit_code_error):
    """ Parses output of jfed_cli tool and returns result as dict """
    extractors = [
        ############################################################################
        #    general
        ############################################################################
        {
            'label': 's4cred',
            'regex': r'^Using speaksFor credential for user "([^"]*)".*$',
        },
        {
            'label': 'existsbefore',
            'regex': r'^slice urn:[^ ]+ (.*)$',
            'mapper': {
                'does not yet exist': False,
                'already exists': True,
            }
        },
        {
            'label': 'error',
            'regex': r'^Error: The slice urn:[^ ]+ (does not exist. Cannot continue.)$',
            'mapper': {
                'does not exist. Cannot continue.': 'DOES_NOT_EXIST'
            }
        },
        {
            'label': 'large_error',
            'regex': r'^(Error [^:^\n]+): ',
        },
        ############################################################################
        #    slice and sliver creates
        ############################################################################
        {
            'label': 'sliver_available',
            'regex': r'^(The sliver is ready.)$',
            'mapper': {
                'The sliver is ready.': True
            },
        },
        {
            'label': 'check_status_requests',
            'regex': r'^Contacting (urn:[^ ]+) to check status...$',
            'multiple': True,
        },
        {
            'label': 'check_status_responses',
            'regex': r'^Status of sliver at +urn:[^ ]+ is ([^ ]+)$',
            'multiple': True,
        },
        {
            'label': 'create1',
            'regex': r'^Sliver at +(urn:[^ ]+) is created and initializing...$',
        },
        {
            'label': 'create2',
            'regex': r'^(Will now wait until the sliver is ready...)$',
        },
        ############################################################################
        #    slice and sliver renews
        ############################################################################
        {
            'label': 'contact',
            'regex': r'^Contacting  (urn:[^ ]+)...$',
        },
        {
            'label': 'requested_exp_date',
            'regex': r'^Renewing slice, requested new expire date is ([^ ]+) ...$',
        },
        {
            'label': 'requested_sliver_renews',
            'regex': r'^Renewing sliver at +(urn:[^ ]+) to expire at [^ ]+$',
            'multiple': True,
        },
        {
            'label': 'successfull_sliver_renews',
            'regex': r'^Sliver at +(urn:[^ ]+) has been renewed successfully$',
            'mapper': {
                'has been renewed successfully': True
            },
            'multiple': True,
        },
        ############################################################################
        #    slice and sliver deletes
        ############################################################################
        {
            'label': 'deleted_from_authorities',
            'regex': r'^Slivers at +(urn:[^ ]+) have been deleted.$',
            'multiple': True,
        },
        {
            'label': 'unregistered_from_authorities',
            'regex': r'^Slivers at +(urn:[^ ]+) has been unregistered.$',
            'multiple': True,
        },
    ]
    outdict = {
        'is_exit_code_error': is_exit_code_error,
    }
    for extractor in extractors:
        regexstr = extractor['regex']
        label = extractor['label']
        mapper = extractor.get('mapper', False)
        multiple = extractor.get('multiple', False)
        while True:
            match = re.search(regexstr, output, flags=re.MULTILINE)
            if match:
                # Get value that is between brackets in regex
                value = match.group(1).lstrip()
                if mapper:
                    try:
                        value = mapper[value]
                    except KeyError:
                        pass
                if multiple:
                    outdict[label] = outdict.get(label, []) # None -> empty list
                    outdict[label].append(value)
                else:
                    outdict[label] = value
                # Remove matched string from output
                output = re.sub(regexstr, '', output, flags=re.MULTILINE)
            if match and multiple:
                # Check again if multiple and one is found.
                pass
            else:
                break
    # Sanitize output
    output = output.lstrip().lstrip('"').rstrip().rstrip('"')
    # Only thing left should be json object. Can be empty, Error or result.
    if output != '':
        try:
            output = output.lstrip('"').rstrip().rstrip('"')
            outdict['json_output'] = json.loads(output)
        except ValueError:
            raise ValueError('Cannot convert output to json: {}'.format(output))
    print "DEBUG: outdict = {}".format(outdict)
    return outdict
