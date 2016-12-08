Juju Client Hacking Tips
========================

Running tests
-------------

In order to run the tests a Juju environment must be bootstrapped manually for
the tests to interact.  Do the following to run against an ec2 environment::

    $ juju bootstrap -e ec2

Once the environment is correctly bootstrapped , you can run the tests with:

    $ JUJU_TEST_ENV="$(juju switch)" tox -e py27 # Also you can use py33, py34 and pep8 targets, see tox.ini
