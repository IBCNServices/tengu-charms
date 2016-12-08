Examples
========


Deploy a local charm
++++++++++++++++++++

Say we have a charm we're developing locally in the directory
`mydatabase` for ubuntu trusty. We can deploy that charm to the
a juju environment with the following::

   >>> result = env.add_local_charm_dir('mydatabase', 'trusty')
   >>> env.deploy('mydb', result['CharmURL']

Which allocate a vm from the iaas provider using the trusty image and
deploy the charm to it.

We can relate it to an extant wordpress application via::

   >>> env.add_relation('mydb', 'myblog')


Sharing Shell Access
++++++++++++++++++++

If your working with a colleague and want to give them shell
access to the environment using their github username::

   >>> env.keys.import_keys('admin', 'gh:kapilt')

We'd like them to have a look at one troublesome machine in particular,
first we need to get the address of that machine::

   >>> env.get_public_address('7')
   {u'PublicAddress': u'104.236.93.117'}

And now we can tell our colleague to ssh directly into that machine.

Note this requires a version of juju with the KeyManager API,
we can verify that our env has that via::

   >>> 'KeyManager' in env.facades
   True

   
Scaling a service
+++++++++++++++++

If we're deploying a cloud service chances are we'd like to scale
it up and down on demand to take advantage of utility nature
of cloud computing.

To do that we've setup a monitoring system (aws cloudwatch, zabbix,
graphite, etc.) that has alerts for low and high thresholds.

So we'll write two scripts one for alerts to scale up::

   #!/usr/bin/python
   from jujuclient import Environment
   
   # Max number of units we want to have to control costs.
   MAX_UNITS = 10

   # This is the service we want to scale.
   SERVICE = 'myapp'

   def up():
       env = Environment.connect('cloud')
       unit_count = len(env.status('myapp')['Units'])
       headroom = MAX_UNITS - unit_count
       if (headroom - 1) < 0:
          print "oops we don't want to spend anymore"
	  return
       # We could scale up in other increments with more
       # logic here.
       env.add_units(SERVICE, num_units=1)

   up()


And another script to scale down.

.. code-block:: python


   #!/usr/bin/python
   from jujuclient import Environment
   
   # Max number of units we want to have to control costs.
   MIN_UNITS = 2

   # This is the service we want to scale.
   SERVICE = 'myapp'

   def down():
       env = Environment.connect('cloud')
       service_units = env.status('myapp')['Units'])
       if len(service_units) <

       unit_ids = sorted(env.status('myapp')['Units'])[:-STEP]
       headroom = unit_count - MIN_UNITS
       if headroom - 1< 0:
          print "need to maintain minimum level of service"
	  return
       # LIFO removal of unit (albeit ascii sorted).
       env.remove_units(SERVICE, sorted(service_units)[-1])

   down()

We can hook them up to our monitoring threshold alarms for high and
low load and we're done.
