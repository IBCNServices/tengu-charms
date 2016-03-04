# tengu-management

The Tengu management tools allow you to create and destroy Tengu environments.

# Usage

After installation, the management functions are available using the `tengu` command. It has the following functions:

    Usage: tengu.py [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      create            Create a Tengu with given name.
      deploy            Create a Tengu with given name.
      destroy           Destroys Tengu with given name NAME: name of...
      downloadbigfiles  Download bigfiles in $JUJU_REPOSITORY
      export            Export Tengu with given NAME
      import            Import Tengu from config file
      juju              Juju related commands
      lock              Lock destructive actions for given Tengu...
      renew             Set expiration date of Tengu to now + given...
      status            Show status of Tengu with given name NAME:...
      unlock            Lock destructive actions for given Tengu...
      userinfo          Print info of configured jfed user


# OpenVPN config

After creating a Tengu, this tool automatically installs an OpenVPN server to machine `0`. You can get the client configuration to connect to the VPN by running `juju scp openvpn/0:~/client1.tgz .` on your Hauchiwa.
