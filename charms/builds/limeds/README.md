# LimeDS

## What is it?

The LimeDS framework provides a visual toolset, allowing developers to rapidly wire together data-driven services in their programming language of choice. Built-in support for service reliability, scalability and caching makes it the ideal companion for developers aiming to speed up the creation of data-driven software.

## Why use it?

LimeDS allows developers to immediately focus on the use-case specific implementation. This is made possible thanks to a visual editor used for drawing dataflows, that will generate well-behaving modules following the micro services design pattern.

More information on [the LimeDS website](http://limeds.intec.ugent.be/)

## How to use

Deploy docker

    juju deploy cs:~tengu-team/docker

Deploy the limeds charm

    juju deploy cs:~tengu-team/limeds --to docker/0

Add relation between the docker engine and limeds

    juju add-relation limeds docker

Check the deployment status (press <kbd>ctrl</kbd>-<kbd>c</kbd> to exit)

    watch -c juju status --color

When the deployment is done ('active', 'Ready'), surf to `<ip>:<port>/editor` and login with admin:admin to see the management console.

# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](https://tengu.io), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
