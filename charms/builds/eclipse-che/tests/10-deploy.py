#!/usr/bin/env python3

# This is a very basic test to make sure the Charm installs correctly. This
# Charm is more or less useless without the Docker layer, so more extensive
# testing should be done in the bundle tests.

import re

import unittest
import requests
import amulet

SECONDS_TO_WAIT = 1200


class TestDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Perform a one time setup for this class deploying the charms."""
        cls.deployment = amulet.Deployment(series='xenial')

        cls.deployment.add('eclipse-che')

        cls.deployment.setup(timeout=SECONDS_TO_WAIT)
        # Wait for the system to settle down.
        application_messages = {
            'eclipse-che': re.compile(r'Ready \(eclipse/che'),
        }
        cls.deployment.sentry.wait_for_messages(application_messages,
                                                timeout=600)
        cls.che = cls.deployment.sentry['eclipse-che']

    def test_dashboard(self):
        self.deployment.expose('eclipse-che')
        url = self.get_url("/dashboard")
        teststring = "<!doctype html>"
        response = requests.get(url)
        self.assertTrue(
            response.status_code == 200,
            "unable to access Eclipse Che Dashboard")
        self.assertTrue(
            teststring in response.text,
            "Eclipse Che Dashboard response "
            "not recognized: {}".format(response.text)
            )

    def get_url(self, path):
        """ Return complete url including port to path"""
        base_url = "http://{}:{}".format(
            self.che[0].info['public-address'],
            self.che[0].info['open-ports'][0].split('/')[0])
        return base_url + path


if __name__ == '__main__':
    unittest.main()
