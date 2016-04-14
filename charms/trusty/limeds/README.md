# LimeDS

## What is it?

The LimeDS framework provides a visual toolset, allowing developers to rapidly wire together data-driven services in their programming language of choice. Built-in support for service reliability, scalability and caching makes it the ideal companion for developers aiming to speed up the creation of data-driven software.

## Why use it?

LimeDS allows developers to immediately focus on the use-case specific implementation. This is made possible thanks to a visual editor used for drawing dataflows, that will generate well-behaving modules following the micro services design pattern.

More information on [the LimeDS website](http://limeds.intec.ugent.be/) and [the LimeDS public wiki](https://bitbucket.org/ibcndevs/limeds-framework/wiki/Home)

## How to use

Deploy limeds

    juju deploy local:limeds --to lxc:0

Check the deployment status (press <kbd>ctrl</kbd>-<kbd>c</kbd> to exit)

    watch juju status --format tabular

When the deployment is done ('active', 'Ready'), surf to `<limeds>/system/console` and login with admin:admin to see the management console.

You can connect LimeDS to MongoDB

    juju add-relation limeds mongodb
