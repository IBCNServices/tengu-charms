# Overview

This Charm deploys the [Jupyter notebook](http://jupyter.org) and randomly generates [an easy to remember password](https://xkcd.com/936/).

The Jupyter Notebook is a web application that allows you to create and share documents that contain live code, equations, visualizations and explanatory text. Uses include: data cleaning and transformation, numerical simulation, statistical modeling, machine learning and much more.

# Usage

This Charm deploys the Jupyter notebook and shows the generated password as part of the status message. You can see the password by running `juju status` or looking at the details of the deployed unit in the Juju GUI.

```
$juju status
Unit                 Workload  Agent  Machine   Public address  Ports     Message
jupyter-notebook/0   active    idle   0         192.168.0.1     8888/tcp  Ready (Pass: "shmuck technical eschew Aqaba")
```

# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Sebastien Pattyn <sebastien.pattyn@qrama.io>
 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>
