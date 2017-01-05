# LimeDS

## What is it?

The LimeDS framework provides a visual toolset, allowing developers to rapidly 
wire together data-driven services in their programming language of choice. 
Built-in support for service reliability, scalability and caching makes it the 
ideal companion for developers aiming to speed up the creation of data-driven 
software.

## Why use it?

LimeDS allows developers to immediately focus on the use-case specific 
implementation. This is made possible thanks to a visual editor used for 
drawing dataflows, that will generate well-behaving modules following the micro
services design pattern.

More information on [the LimeDS website](http://limeds.intec.ugent.be/)

## How to use

Deploy docker

Deploy the limeds subordinate charm

    juju deploy limeds

Add relation between the docker engine and limeds

    juju add-relation limeds docker

Check the deployment status (press <kbd>ctrl</kbd>-<kbd>c</kbd> to exit)

    watch juju status

When the deployment is done ('active', 'Ready'), surf to `<limeds>/editor` and login with admin:admin to see the management console.
