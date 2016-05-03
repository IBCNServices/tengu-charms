#!/bin/bash
#sudo pip2 install click pyyaml
#echo '/opt/tengu/scripts/tengu.py "$@"' | sudo tee /usr/bin/tengu
#sudo chmod a+x /usr/bin/tengu
sudo cp -r /opt/tengu/scripts /opt/tengu/scripts.bak`date "+%y-%d-%m_%H:%M:%S"`
sudo rm -r /opt/tengu/scripts/*
sudo cp -r . /opt/tengu/scripts/
