# LimeDS installable

This Charm adds an installable to LimeDS and creates a segment that you can use in your slices. For more installables: https://bitbucket.org/ibcndevs/limeds-framework/wiki/Home#Modules

# Usage

```bash
# Deploy the LimeDS bundle
juju deploy cs:~tengu-team/limeds-core
# Deploy the LimeDS installable plugin
juju deploy cs:~tengu-tean/limeds-installable

# Expose the Docker container where LimeDS is running
juju expose docker
```

Watch it being deployed using `watch -c juju status --color` (close using <kbd>ctrl</kbd>-<kbd>c</kbd>).

```
App          Version  Status  Scale  Charm        Store       Rev  OS      Notes
docker                   active       1  docker          jujucharms    3  ubuntu  exposed
limeds                   active       1  limeds          local         1  ubuntu
limeds-mongodb           active       1  limeds-mongodb  local         1  ubuntu
mongodb                  unknown      1  mongodb         jujucharms   37  ubuntu

Unit                 Workload  Agent      Machine  Public address  Ports                                    Message
docker/0*            active    idle       38       54.165.156.82   32768/tcp                                Ready
limeds/0*            active    idle       38       54.165.156.82                                            Ready (ibcndevs/limeds)
  limeds-installable/0* active idle                54.165.156.82                                            Ready (MyInstallable)
mongodb/0*           unknown   idle       39       107.23.144.223  27017/tcp,27019/tcp,27021/tcp,28017/tcp
```

After deployment, go to `http://<docker-url>:<docker-port>/editor` and import the segment to your slice.


# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](https://tengu.io), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
