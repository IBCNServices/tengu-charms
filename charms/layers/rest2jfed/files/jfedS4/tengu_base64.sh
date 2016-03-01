#!/bin/sh

#sed -i -e 's/<[^>]*>//g' $1
sed -i -e 's/ /+/g' $1
sed -i -e 's/\"//g' $1
base64 -d $1
