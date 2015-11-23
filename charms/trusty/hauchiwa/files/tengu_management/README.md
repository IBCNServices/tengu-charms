# tengu-management

The tengu management GUI can be installed either as a standalone program or as part of the [tengu-instance-management charm](https://github.ugent.be/Tengu/tengu-charms/tree/master/charms/trusty/tengu-instance-management).

# Installation

Install the tengu management tool as standalone program by running `./install` in the root folder of this repository.

# Usage

After installation, the management functions are available using the `tengu` command. It has the following functions:

    tengu create <environment-name>
        - Create tengu environment config files from default config
        - Create jfed experiment with same name if it doesn't exist
        - Create Juju environment from default environment config
        - Adds all the machines of the jfed experiment to the juju environment
        - Installs `juju-gui` to machine 0 (the bootstrap-host / state server)

    tengu destroy <environment-name>
        destroys the environment and removes it from the environment.yaml config file. This command is very generous, it will remove even the most broken environments. It does not destroy the jfed experiment.

    tengu configure <environment-name>
        asks the user configuration options for the specified environment


Legacy commands: (not yet supported in v2.0)

    tengu status
        shows a summary of machines and charms

# Juju

The tengu management tool runs on top of Juju. Following are some useful commands:

    juju status
    juju debug-hooks $NODE      # example: NODE="nimbus/0"
    juju ssh $NODE
    juju resolved $NODE [--retry]
