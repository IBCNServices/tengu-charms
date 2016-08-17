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

This git repository doesn't contain big files like binaries and tarballs. You have to download these binaries before you can deploy Charms from this repository. The `tengu downloadbigfiles` tool downloads the binaries and puts them in the correct folder. **This tool is installed by default on a Hauchiwa and is run once during installation.**

If you add a `<filename>.source` file in a folder, `tengu downloadbigfiles` will download the source to that folder as `<filename>`. The `<filename>.source` file either specifies a url or a download command. The `<filename>.source` file can optionally specify that the downloaded file should be extracted. This is the format:

    <url>         # url to download resource from
    [<action>]    # action to execute after download. Currently only 'extract' is supported

or

    command: <download command>     # command to execute in order to download resource
    [<action>]                      # action to execute after download. Currently only 'extract' is supported

The second format can be used when you need to add custom cookies and headers to the download request. This is for example needed when downloading oracle java [as used in the rest2jfed charm](https://github.com/IBCNServices/tengu-charms/blob/390256d7eafa86a7b50bb46c4c6b5f22ff4739cc/charms/trusty/rest2jfed/files/server-jre-8u45-linux-x64.tar.gz.source).


## Layers

Both the resulting Charms and the source layers of layered Charms are located in this repository. Changes to layered Charms have to be made to the corresponding layers in their `charms/layers/<layerName>` directory. **Do not** make changes to the charm in `charms/<series>/<charmName>` directory if it is a layered charm! **Changes will be overwritten after rebuilding the Charm!**

After editing the layers, you can regenerate the layer by running `charm generate <top-layer-name>`. It is advised to do this in a python virtualenv to avoid contamination between your host, the charm tools and the layer dependencies.

    sudo apt-get install python-virtualenv
    virtualenv charm-tools           # create the virtualenv
    . charm-tools/bin/activate       # go inside the virtualenv
    pip install -U charm-tools pip   # install charm-tools

*Note: Layered Charms run python 3 be default and install `pip3` as default `pip` installation.*

## Dev environment

I'm using Atom on Ubuntu with some extentions. Here's how I installed everything:

    # Install Atom:
    sudo add-apt-repository ppa:webupd8team/atom
    sudo apt-get update
    sudo apt-get install atom

    # Install python package manager
    sudo apt install python-pip python3-pip python-setuptools python3-setuptools

    # Pyton linting (code checking) for both python 2 and python 3
    sudo pip2 install pylint
    sudo pip3 install pylint
    apm install linter linter-pylint
    mkdir ~/bin
    # add lib directory of charms to pylint path
    # %f/../lib

`nano ~/bin/pylint` and add:

    #!/bin/bash
    if [[ $(head -n 1 "${@: -1}") == *python3* ]]
    then
      pylint3 --extension-pkg-whitelist=lxml,netifaces "$@"
    else
      pylint2 --extension-pkg-whitelist=lxml,netifaces "$@"
    fi


`nano ~/bin/pylint2` and add:

    #!/usr/bin/python2
    # EASY-INSTALL-ENTRY-SCRIPT: 'pylint','console_scripts','pylint'
    __requires__ = 'pylint'
    import sys
    from pkg_resources import load_entry_point

    if __name__ == '__main__':
        sys.exit(
            load_entry_point('pylint', 'console_scripts', 'pylint')()
        )

`nano ~/bin/pylint3` and add:

    #!/usr/bin/python3
    # EASY-INSTALL-ENTRY-SCRIPT: 'pylint','console_scripts','pylint'
    __requires__ = 'pylint'
    import sys
    from pkg_resources import load_entry_point

    if __name__ == '__main__':
        sys.exit(
            load_entry_point('pylint', 'console_scripts', 'pylint')()
        )

and finally: `chmod u+x ~/bin/pylint ~/bin/pylint2 ~/bin/pylint3`. Log out and log back in to save the changes.

**Charm tools: helper tools to Charm.**

    # Juju Charm tools
    sudo apt-get install charm-tools juju-deployer

    sudo apt install python-pip
    sudo pip install charmhelpers
    sudo pip2 install Flask

    # Dependencies of Charms so linter can check them
    sudo pip2 install click
    sudo pip3 install charms.reactive netifaces amulet click

    # Other atom packages
    apm install language-groovy


When running `juju debug-hooks`, you enter a tmux session. The default tmux bindings on Ubuntu are a bit strange. ctrl-a is the default command. To enable sane mouse scrolling set `set-window-option -g mode-mouse on` in `~/.tmux.conf` of the server.

## Handy commands

debug reactive framework

charms.reactive -p get_states

pull PR from github

    git pull origin pull/$PR_NUM/head

prettyprint json output

    | python -m json.tool

grep and get text around match

    cat log | grep -A10 <searchterm> # Next 10 lines
    cat log | grep -B10 <searchterm> # Previous 10 lines

Debug IP traffic:

iptables -I INPUT -j LOG --log-prefix "Connection: "


Mongo

    show dbs
    use db demo
    show collections
    coll = db['imec']
    coll.find().skip(coll.count() - 20)
    coll.find({"subscriptionId": { $exists : true }}).limit(1).sort({$natural:-1})
    ObjectId("5714784653628548824c18de").getTimestamp()

cat /var/lib/dhcp/dhcpd.leases


**disk space analyseren**

    tree -h --du /var | grep "G]"
    sudo du -h /var | grep '[0-9\.]\+G'

**reconnect to screen**
    screen -r

# Default Tengu license:

## Plain text

```
Copyright (C) 2016  Ghent University

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

```

## Hash comments

```
# Copyright (C) 2016  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

```
