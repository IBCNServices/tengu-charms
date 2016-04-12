#!/bin/bash
sudo cp -r /opt/tengu/scripts /opt/tengu/scripts.bak`date "+%y-%d-%m_%H:%M:%S"`
sudo rm -r /opt/tengu/scripts/*
sudo cp -r . /opt/tengu/scripts/
