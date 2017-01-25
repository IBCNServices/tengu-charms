Run Eclipse Che


```bash
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -e CHE_HOST=172.28.0.34 -e CHE_PORT=8081 -v /home/ubuntu/:/data eclipse/che start
```

`~/che.env`:

```bash
CHE_HOST=172.28.0.34

#...

CHE_DOCKER_IP_EXTERNAL=172.28.0.34
```

Custom stack


[Recipes Docs](https://eclipse-che.readme.io/v5.0/docs/recipes)


```Dockerfile
FROM jujusolutions/jujubox
EXPOSE 22
RUN sudo apt-get install -qy \
    openssh-server \
    nano tree && \
    sudo mkdir /var/run/sshd && \
    sudo sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENTRYPOINT sudo /usr/sbin/sshd -D && \
    tail -f /dev/null
```


```Dockerfile
FROM ubuntu:16.04

EXPOSE 4403 8000 8080 9876 22

ARG JUJU_USER=ubuntu

ENV JUJU_HOME /home/$JUJU_USER/.juju
ENV JUJU_REPOSITORY /home/$JUJU_USER/charms

RUN useradd -m $JUJU_USER -s /bin/bash

RUN mkdir -p $JUJU_HOME
RUN mkdir -p $JUJU_REPOSITORY

RUN chown -R $JUJU_USER:$JUJU_USER $JUJU_HOME
RUN chown -R $JUJU_USER:$JUJU_USER $JUJU_REPOSITORY

VOLUME [ "$JUJU_HOME", "$JUJU_REPOSITORY" ]

RUN apt-get update -qq && \
    apt-get install -y software-properties-common && \
    apt-add-repository -u -y ppa:juju/stable && \
    apt-get install -qy \
        openssh-server \
        byobu \
        juju \
        openssh-client \
        python \
        python3 \
        sudo \
        vim && \
    mkdir /var/run/sshd && \
    sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd && \
    echo "${JUJU_USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/juju-users && \
    mkdir -p /home/$JUJU_USER/.ssh && \
    chmod 700 /home/$JUJU_USER/.ssh && \
    echo 'Host *' > /home/$JUJU_USER/.ssh/config && \
    echo '  StrictHostKeyChecking no' >> /home/$JUJU_USER/.ssh/config && \
    chmod 400 /home/$JUJU_USER/.ssh/config && \
    chown -R $JUJU_USER:$JUJU_USER /home/$JUJU_USER/.ssh && \
    JUJU_VERSION=`juju version` && \
    RC=/home/$JUJU_USER/.bashrc && \
    echo "echo Welcome to jujubox version ${JUJU_VERSION}" >> $RC && \
    apt-get autoremove -qy && \
    apt-get autoclean -qy && \
    apt-get clean -qy

USER $JUJU_USER

WORKDIR /home/$JUJU_USER

CMD sudo /usr/sbin/sshd -D && \
    tail -f /dev/null
```

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
