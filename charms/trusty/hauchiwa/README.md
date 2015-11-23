# Overview

This Charm sets up a Tengu hauchiwa.

# Usage

Install Charm and add relation.

    juju deploy local:hauchiwa --config tia-cfg.yaml
    juju deploy local:rest2jfed --config rest2jfed-cfg.yaml
    juju add-relation rest2jfed hauchiwa

# Configuration

In order to succesfully use `tengu`, this charm requires two things:
1. A relation with a correctly configured rest2jfed Charm.
2. Both the `emulab-project-name` and the `emulab-s4-cert` config options need to be specified. This can be done after the deployment using `juju set` or during the deployment using the `--config filename.yaml` flag pointing to a config file in following format:
    hauchiwa:
        emulab-s4-cert: '<base64 s4-cert>'
        emulab-project-name: <project-name>

The `emulab-s4-cert` has to give permission to the user specified in the rest2jfed Charm.

# Contact Information

Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
