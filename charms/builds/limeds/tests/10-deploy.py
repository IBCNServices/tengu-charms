#!/usr/bin/env python3

# This is a very basic test to make sure the Charm installs correctly. This
# Charm is more or less useless without the Docker layer, so more extensive
# testing should be done in the bundle tests.

import re

import unittest
import amulet

SECONDS_TO_WAIT = 1100


class TestDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Perform a one time setup for this class deploying the charms."""
        cls.deployment = amulet.Deployment(series='xenial')

        cls.deployment.add('limeds')

        cls.deployment.setup(timeout=SECONDS_TO_WAIT)
        # Wait for the system to settle down.
        application_messages = {
            'limeds': re.compile('docker'),
        }
        cls.deployment.sentry.wait_for_messages(application_messages,
                                                timeout=600)
        cls.limeds = cls.deployment.sentry['limeds']

    def test_dummy(self):
        pass


if __name__ == '__main__':
    unittest.main()
