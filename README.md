# Tengu

Tengu is a flexible and dynamic data platform that can adapt to your needs. Tengu makes it possible to quickly set up and test a number of different data technologies such as Hadoop, Spark, Storm and Kafka. Tengu gives users the ability to connect different data technologies in order to get a complete distributed data solution. Tengu makes it possible to integrate with existing data and automation infrastructure. Existing automation artifacts such as Chef cookbooks and Puppet scripts can be reused to ease the transition to and integration with Tengu.

Tengu enables a number of use-cases:

 - Tengu provides a sandbox that enables guided experimentation with data tools. **Companies that want to get started with big data technologies** can use Tengu to build and test different big data solutions to see what fits their use-case.
 - **Companies that want to integrate big data tools into their existing infrastructure** can use Tengu to manage the integration between big data tools and their existing data infrastructure. Because Tengu is automation-tool independent, it can easily reuse existing automation artifacts such as Chef cookbooks and Puppet scripts.
 - **Developers that want to accelerate adoption of their data tools** can capture the operational knowledge of their data tool in Tengu to allow fast and easy deployment and integration.

## Integrating a project into Tengu

When you integrate your data tool into Tengu, user can very easily integrate your tool in their workflows. By using [Juju](https://jujucharms.com/) at its core, Tengu enables you to connect your data tool to the wide range of tools already available in Tengu.

When you write a Juju Charm, you capture the best practice operational knowledge of your data tool and enable others to reuse this knowledge. The first step is to capture the knowledge of how to **install and configure** your data tool. This enables users to rapidly deploy and test your data tool. The second step is to capture the knowledge of the options for **communication and collaboration with other data tools**. When you implement existing interfaces in your Charm, **users can swap out existing data tools and replace them by your data tool.** This enables very fast adoption of new data tools.

The Juju docs contain a good [high-level overview of what Juju is](https://jujucharms.com/docs/stable/about-juju). Are you planning to integrate you data tool and want some guidance? Don't hesitate to contact us! You can contact me at [merlijn.sebrechts@gmail.com](mailto:merlijn.sebrechts@gmail.com).

## Tengu Charms

This repository contains all the Open Source Charms, Bundles, Interfaces and Layers of the [Tengu platform](gettengu.io/). This repository is the upstream for the Tengu Charms available in the Charm Store.

Most of the Tengu services, like `rest2jfed` and `tengu-instance-admin`, are contained in their Charms in this repository and do not have a seperate upstream project.

This repository does not contain the required bundles to deploy the Tengu platform as a whole, since those bundles contain "private" config options like private keys. Those bundles can be accessed in [the private Tengu repository](https://github.ugent.be/Tengu/private) if you have the correct credentials.

# Tengu developer info

Tengu uses Juju at its core. Juju is used to

## Bigfiles

This repository doesn't contain big files like binaries and tarballs. Those need to be downloaded seperately. Each big file hase a corresponding source file named `<bigfileLocation>/<bigfileName>.source`. This file can have two formats:

    <url>         # url to download resource from
    [<action>]    # action to execute after download. Currently only 'extract' is supported

or

    command: <download command>     # command to execute in order to download resource
    [<action>]                      # action to execute after download. Currently only 'extract' is supported

The second format can be used when you need to add custom cookies and headers to the download request. This is for example needed when downloading oracle java.


## Layers

Both the resulting Charms and the source layers of layered Charms are located in this repository. Changes to layered Charms have to be made to the corresponding layers in their `charms/layers/<layerName>` directory. **Do not** make changes to the charm in `charms/<series>/<charmName>` directory if it is a layered charm! **Changes will be overwritten after rebuilding the Charm!**

After editing the layers, you can regenerate the layer by running `charm generate <top-layer-name>`. It is advised to do this in a python virtualenv to avoid contamination between your host, the charm tools and the layer dependencies.

    sudo apt-get install python-virtualenv
    virtualenv charm-tools           # create the virtualenv
    . charm-tools/bin/activate       # go inside the virtualenv
    pip install -U charm-tools pip   # install charm-tools

*Note: Layered Charms run python 3 be default and install `pip3` as default `pip` installation.*

## Dev environment

I'm using atom with some extentions. Following commands install the correct extentions:

    # Pyton linting (code checking)
    sudo apt-get install pylint
    apm install linter
    apm install linter-pylint

    # Juju Charm tools
    sudo apt-get install charm-tools

    sudo apt install python-pip
    pip install charmhelpers


As security measure, Python-linting doesn't load c extentions by default. I whitelist the libraries that use c extensions by making the executable script `pylint.sh`:

    pylint --extension-pkg-whitelist=lxml,netifaces "$@"

and setting this script as "Pylint Executable" in the `linter-pylint` module.


When running `juju debug-hooks`, you enter a tmux session. The default tmux bindings on Ubuntu are a bit strange. ctrl-a is the default command. To enable sane mouse scrolling set `set-window-option -g mode-mouse on` in `~/.tmux.conf` of the server.
