#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

    # This is a very basic test to make sure the Charm installs correctly. This
    # Charm is more or less useless without the Docker layer, so more extensive
    # testing should be done in the bundle tests.
    def test_dummy(self):
        pass


if __name__ == '__main__':
    unittest.main()
