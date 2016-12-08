Introduction
============

A simple synchronous python client for the juju-core client websocket
api that powers the cli and juju-gui. Supports both python 2.7 and
python 3.4

It has high fidelity coverage of the juju-core api, including the various
facade api extensions.

Installation
++++++++++++

Either via packages (see juju-stable/ppa) ala::

  $ sudo apt-get install python-jujuclient

or via python packages::

  $ virtualenv jujuclient
  $ source jujuclient/bin/activate
  $ pip install jujuclient pyyaml


Connecting
++++++++++

To facilitate simple client usage the easiest way to connect to an environment
is via the connect classmethod helper using the environment name::

  >>> from jujuclient import Environment
  >>> env = Environment.connect('ocean')


Facade Usage
++++++++++++

Juju provides for multiple apis behind a single endpoint with
different apis segmentations known as 'facades', each facade is
versioned independently. This client provides for facade auto
negotiation based on login results to provide the best matching client
version. The facades are directly annotated onto the env/client
instance.

The extant facades implemented by this client for juju 1.23 are
Charms, KeyManager, UserManager, HighAvailability, Action, and
Annotations.

The available facades are exposed as an attribute of the client::

   >>> pprint.pprint(env.facades)

   {'Action': {'attr': 'actions', 'version': 0},
    'Annotations': {'attr': 'annotations', 'version': 1},
    'Backups': {'attr': 'backups', 'version': 0},
    'Charms': {'attr': 'charms', 'version': 1},
    'EnvironmentManager': {'attr': 'mess', 'version': 1},
    'HighAvailability': {'attr': 'ha', 'version': 1},
    'ImageManager': {'attr': 'images', 'version': 1},
    'KeyManager': {'attr': 'keys', 'version': 0},
    'UserManager': {'attr': 'users', 'version': 0}}

Each of these is available as the named attribute from the client::

   >>> env.charms.list()
   {'CharmURLs': ['cs:~hazmat/trusty/etcd-6']}

   >>> env.users.list()
   {'results': [{'result': {
        'username': 'admin',
        'date-created': '2015-01-27T14:55:22Z',
        'disabled': False,
        'created-by': 'admin',
        'last-connection': '2015-01-27T20:42:33Z',
        'display-name': 'admin'}}]}
