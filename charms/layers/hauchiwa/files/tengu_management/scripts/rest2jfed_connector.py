""" Module for connecting to the rest2jfed server """
import base64
import requests
import json
#import pprint
#PPRINTER = pprint.PrettyPrinter()

from output import fail # pylint: disable=F0401


class Rest2jfedConnector(object):
    """ Connects to Rest2jfed server """
    def __init__(self, hostname, port, s4cert_path, projectname,
                 slicename, locked=True):
        self.hostname = hostname
        self.port = port
        self.projectname = projectname
        self.slicename = slicename
        self.locked = locked
        with open(s4cert_path, 'r') as s4cert_file:
            s4cert = s4cert_file.read()
        self.headers = {'emulab-s4-cert': base64.b64encode(s4cert)}


    def get_userinfo(self):
        """ Gets userinfo """
        url = self.userinfo_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def get_sliceinfo(self):
        """ Gets sliceinfo """
        url = self.sliceinfo_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def get_status(self):
        """ Gets status of jfed slice """
        url = self.status_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def get_full_status(self):
        """ Gets status of jfed slice return dict"""
        url = self.status_url
        response = requests.get(
            url,
            params={'extended':'true'},
            headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def get_manifest(self, manifest_path):
        """ Gets the manifest of jfed slice (if it exists)"""
        url = self.slice_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            with open(manifest_path, 'r+') as manifest_file:
                manifest_file.write(response.content)
            return
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def exp_exists(self):
        """Checks if jFed experiment exists."""
        url = self.exists_url
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def create(self, rspec_path, manifest_path):
        """ Creates jfed slice """
        with open(rspec_path, 'r') as rspec_file:
            rspec_contents = rspec_file.read()
        url = self.slice_url
        response = requests.post(url, data=rspec_contents,
                                 headers=self.headers)
        if response.status_code == 201:
            with open(manifest_path, 'w+') as manifest_file:
                manifest_file.write(response.content)
            return
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def renew(self, exp_time):
        """ Renews jfed slice """
        exp_time = str(exp_time)
        url = self.exp_url
        response = requests.post(url, data=exp_time,
                                 headers=self.headers)
        if response.status_code == 200:
            return json.loads(response.content)
        raise Exception(
            "Call to {2} failed with code {0} and message:\n{1}".format(
                response.status_code, response.text, url))


    def delete(self):
        """ Deletes jfed slice """
        if self.locked:
            fail("Environment is locked, cannot delete it.")
        else:
            url = self.slice_url
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 200:
                return
            raise Exception(
                "Call to {2} failed with code {0} and message:\n{1}".format(
                    response.status_code, response.text, url))


    @property
    def userinfo_url(self):
        """ Url to get userinfo """
        return '{0}/userinfo'.format(self.host_url)


    @property
    def sliceinfo_url(self):
        """ rest url for slice info """
        return '{0}/info'.format(self.slice_url)


    @property
    def status_url(self):
        """ rest url for status """
        return '{0}/status'.format(self.slice_url)


    @property
    def exp_url(self):
        """ rest url for expiration """
        return '{0}/expiration'.format(self.slice_url)


    @property
    def exists_url(self):
        """ rest url for slice exists """
        return '{0}/exists'.format(self.slice_url)


    @property
    def slice_url(self):
        """ rest url for slice """
        return '{}/projects/{}/slices/{}'.format(
            self.host_url,
            self.projectname,
            self.slicename)


    @property
    def host_url(self):
        """ rest url for slice """
        return 'http://{0}:{1}'.format(
            self.hostname,
            self.port)
