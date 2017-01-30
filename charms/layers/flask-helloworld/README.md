# Overview

This Charm deploys a Hello World webservice based on the Flask Python framework.

# Usage

The following instructions show how to build and deploy this Charm from your local repository.

**1. Build the Charm**

```bash
# $JUJU_REPOSITORY should point to the directory of your Juju Charms project
charm build $JUJU_REPOSITORY/layers/flask-helloworld
```

This will build the Charm locally, the built charm will be in `$JUJU_REPOSITORY/builds`. The dependencies defined in `layer.yaml` will be downloaded from [https://interfaces.juju.solutions]().

**2. Deploy the Charm**

```bash
# This will request a new machine from the configured cloud
# provider and deploy the flask-helloworld charm onto that machine.
juju deploy $JUJU_REPOSITORY/builds/flask-helloworld
```

Watch it being deployed using `watch -c juju status --color` (close using <kbd>ctrl</kbd>-<kbd>c</kbd>).

```
Model    Controller         Cloud/Region   Version
default  mycontroller       aws/us-east-1  2.0.2

App               Version  Status  Scale  Charm             Store       Rev  OS      Notes
flask-helloworld           active      1  flask-helloworld  local         2  ubuntu  exposed

Unit                 Workload  Agent  Machine  Public address  Ports                     Message
flask-helloworld/0*  active    idle   1        56.174.83.54    5000/tcp                  Ready

```


# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
