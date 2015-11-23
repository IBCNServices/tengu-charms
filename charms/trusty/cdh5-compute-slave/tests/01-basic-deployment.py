#!/usr/bin/env python3

import unittest
import amulet


class TestDeploy(unittest.TestCase):
    """
    Trivial deployment test for Apache Hadoop Compute Slave.

    This charm cannot do anything useful by itself, so integration testing
    is done in the bundle.
    """

    def test_deploy(self):
        self.d = amulet.Deployment(series='trusty')
        self.d.add('compute-slave', 'apache-hadoop-compute-slave')
        self.d.setup(timeout=900)
        self.d.sentry.wait(timeout=1800)
        self.unit = self.d.sentry['compute-slave'][0]


if __name__ == '__main__':
    unittest.main()
