# Overview

This layer installs and configures the juju-client. It can be used by Charms that want to manage Juju environments.


# Usage

In your charm layer's `composer.yaml`, you will need to include this layer, e.g.:

    includes: ['layers:juju-client']

Don't forget to set COMPOSER_HOME when composing from local layers.

You can react to the states `juju.installed` and `juju.upgraded`. The [`tengu-intance-admin`](https://github.com/galgalesh/tengu-charms/tree/master/charms/layers/tengu-instance-admin) is an example of al layer that uses this layer.

# Options

## charm-repo-source

If specified, downloads and configures local Charms repository from git. Expects a `.git` url.

## environment-*

These options can be used to add an environment to the Juju client instance. You cannot specify more than one environment, since **the ssh keys get overwritten!**

    environment-name:
      type: string
      description: Name of the environment to configure
    environment-config:
      type: string
      description: base64 encoded environment config from environments.yaml
    environment-jenv:
      type: string
      description: base64 encoded environment.jenv file
    environment-pubkey:
      type: string
      description: base64 encoded pubkey file
    environment-privkey:
      type: string
      description: base64 encoded privkey file


[reactive]: http://pythonhosted.org/charms.reactive/
