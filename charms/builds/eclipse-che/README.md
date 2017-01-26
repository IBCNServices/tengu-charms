# Overview

This Charm deploys the latest [Eclipse Che](http://www.eclipse.org/che/). Eclipse Che is a Next-Generation IDE with a developer workspace server.

Your browser becomes your IDE, your workspaces are docker containers. All the development tools, dependencies and libraries are already installed in the workspace. The only thing you have to do is surf to the url and start coding. To top it all off, you get an in-browser terminal right into your workspace.

Choose from a number of ready-to-go workspaces or build your own using Docker containers.
![Choose your stack view ](https://eclipse.org/che/images/features/img-features-stacks.png)

Use the full-featured in-browser commandline.

![IDE + console view  ](https://eclipse.org/che/images/features/img-features-ssh-workspaces.png)

# Usage

To deploy the Charm run `juju deploy cs:~tengu-team/eclipse-che`.

Watch it being deployed using `watch -c juju status --color` (close using <kbd>ctrl</kbd>-<kbd>c</kbd>).

```
Model    Controller         Cloud/Region   Version
default  mycontroller       aws/us-east-1  2.0.2

App          Version  Status  Scale  Charm        Store       Rev  OS      Notes
eclipse-che           active      1  eclipse-che  local         2  ubuntu  exposed

Unit            Workload  Agent  Machine  Public address  Ports                     Message
eclipse-che/0*  active    idle   4        56.174.83.54    8080/tcp,32768-65535/tcp  Ready
```

# Contact Information

## Authors

This software was created in the [IDLab research group](https://www.ugent.be/ea/idlab) of [Ghent University](https://www.ugent.be) in Belgium. This software is used in [Tengu](http://tengu.intec.ugent.be), a project that aims to make experimenting with data frameworks and tools as easy as possible.

 - Merlijn Sebrechts <merlijn.sebrechts@gmail.com>

# Stack Config

```json
{
  "name": "Juju Charm",
  "source": {
    "origin": "ibcnservices/che-charmbox",
    "type": "image"
  },
  "components": [
    {
      "version": "---",
      "name": "charmhelpers"
    },
    {
      "version": "---",
      "name": "bundletester"
    },
    {
      "version": "---",
      "name": "python3"
    },
    {
      "version": "---",
      "name": "charms.reactive"
    }
  ],
  "tags": [],
  "id": "stack1jxs2u1ky1pn3frj",
  "workspaceConfig": {
    "defaultEnv": "charmbox",
    "environments": {
      "charmbox": {
        "machines": {
          "dev-machine": {
            "attributes": {
              "memoryLimitBytes": "2147483648"
            },
            "servers": {},
            "agents": [
              "org.eclipse.che.terminal",
              "org.eclipse.che.ws-agent",
              "org.eclipse.che.ssh"
            ]
          }
        },
        "recipe": {
          "type": "compose",
          "content": "services:\n dev-machine:\n  image: ibcnservices/che-charmbox\n",
          "contentType": "application/x-yaml"
        }
      }
    },
    "projects": [],
    "name": "default",
    "commands": [
      {
        "commandLine": "juju status",
        "name": "Status",
        "attributes": {},
        "type": "custom"
      }
    ],
    "links": []
  },
  "description": "Juju Charm box",
  "creator": "che",
  "scope": "general"
}
```

reactive python project template

```json
[  
  {  
    "name":"reactive-layer",        
    "displayName":"Reactive Layer",
    "path":"/charms/layers",       
    "description":"A Basic reactive layer",
    "projectType":"blank",         
    "mixins":[],                      
    "attributes":{},
    "modules":[],                     
    "problems":[],                   
    "source":{                        
      "type":"git",                  
      "location":"https://github.com/juju-solutions/template-reactive-python.git",                         
      "parameters":{}                 
    },
    "commands":[],
    "links":[],
    "category":"Samples",
    "tags":["python","juju"]
  }
]
```

Projects are in `/projects`
