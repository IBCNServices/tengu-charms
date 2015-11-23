# Tengu Charms

This repository contains all the Open Source Charms, Bundles, Interfaces and Layers of the Tengu platform. This repository is the upstream for the Tengu Charms available in the Charm Store.

Most of the Tengu services, like `rest2jfed` and `tengu-instance-admin`, are contained in their Charms in this repository and do not have a seperate upstream project.

This repository does not contain the required bundles to deploy the Tengu platform as a whole, since those bundles contain "private" config options like private keys. Those bundles can be accessed in [the private Tengu repository](https://github.ugent.be/Tengu/private) if you have the correct credentials.

# Bigfiles

This repository doesn't contain BIGfiles like binaries and tarballs. Those need to be downloaded seperately using the downloadbigfiles script. The source for each bigfile can be found in its corresponding source file: `<bigfileLocation>/<bigfileName>.source`.

# Layers

Both the resulting Charms and the source layers of layered Charms are located in this repository. Changes to layered Charms have to be made to the corresponding layers in their `charms/layers/<layerName>` directory. **Do not** make changes to the charm in `charms/<series>/<charmName>` directory if it is a layered charm! **Changes will be overwritten!**

After editing the layers, you can regenerate the layer by running `charm generate <top-layer-name>`. It is advised to do this in a python virtualenv to avoid contamination between your host, the charm tools and the layer dependencies.

    sudo apt-get install python-virtualenv
    virtualenv charm-tools           # create the virtualenv
    . charm-tools/bin/activate       # go inside the virtualenv
    pip install -U charm-tools pip   # install charm-tools


# Dev environment

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
