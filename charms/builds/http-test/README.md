# Overview

This Charm installs the rest to jfed server. The rest2maas server is automatically started and will restart after a crash. To manually stop the rest2maas server run `sudo service stop` on the node.

# Usage of Charm

Deploy the Charm:

    juju deploy local:rest2maas

To upgrade the charm:

    juju upgrade-charm rest2maas

# Usage of REST application


Create and delete slice:

    POST /projects/<projectname>/slices/<slicename>
        body: contents of requested rspec (xml)
        header: emulab-s4-cert (BASE64)
        returns: manifest (xml)

    DELETE /projects/<projectname>/slices/<slicename>
        header: emulab-s4-cert (BASE64)


Renew slice:

    POST /projects/<projectname>/slices/<slicename>/expiration
    body: requested expiration in hours
    header: emulab-s4-cert (BASE64)


Get manifest and slice status:

    GET /projects/<projectname>/slices/<slicename>
        header: emulab-s4-cert (BASE64)
        returns: manifest (xml)

    GET /projects/<projectname>/slices/<slicename>/status
        header: emulab-s4-cert (BASE64)
        returns: status (DOES_NOT_EXIST,UNALLOCATED,READY,UNKNOWN)


# Debugging

This Charm creates the rest2cli upstart service; starts it and automatically restarts it. Logs are available in `/var/log/upstart/rest2cli.log`. You can manually start, stop and restart the service by running the following commands.

    service rest2cli start
    service rest2cli stop
    service rest2cli restart

Test url: localhost:5000/

Python exceptions are automatically catched in production. To run the server in debug mode, change the last line of the `rest2maas.py` script to `APP.run(host='0.0.0.0, debug=True)`. **Do not run debug mode in production**, since it allows executing arbitrary python code.

# Contact Information

## Bugs

Report bugs on [Github](https://github.com/IBCNServices/tengu-charms/issues).

## Authors

This software was created in the [IBCN research group](https://www.ibcn.intec.ugent.be/) of [Ghent University](http://www.ugent.be/en) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
