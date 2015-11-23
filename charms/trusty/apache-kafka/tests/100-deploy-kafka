#!/usr/bin/python3
import unittest
import amulet


class TestDeploy(unittest.TestCase):
    """
    Deployment test for Apache Kafka
    """

    @classmethod
    def setUpClass(cls):
        cls.d = amulet.Deployment(series='trusty')
        # Deploy Kafka Service
        cls.d.add('kafka', charm='cs:~bigdata-dev/trusty/apache-kafka')
        cls.d.add('zookeeper', charm='cs:~bigdata-dev/trusty/apache-zookeeper')
        cls.d.relate('kafka:zookeeper', 'zookeeper:zookeeper')

        cls.d.setup(timeout=1800)
        cls.d.sentry.wait(timeout=1800)
        cls.unit = cls.d.sentry['kafka'][0]

    def test_deploy(self):
        output, retcode = self.unit.run("pgrep -a java")
        assert 'Kafka' in output, "Kafka daemon is not started"


if __name__ == '__main__':
    unittest.main()
