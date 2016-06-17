# Overview

This Charm sets up a [Tengu](tengu.intec.ugent.be) Hauchiwa. This Hauchiwa can be used to create models on servers from jFed compatible testbed.

# Usage

Install Charm and add relation.

    juju deploy cs:~tengu-bot/hauchiwa
    juju set hauchiwa emulab-s4-cert=`cat s4-cert.xml | base64`
    juju deploy cs:~tengu-bot/rest2jfed
    juju set set emulab-cert=`cat certificate.pem | base64`
    juju add-relation rest2jfed hauchiwa


# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
