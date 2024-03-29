#!/bin/bash

[ -z "$SERVER01" ] && echo "Error: SERVER01 envvar not set." && exit 1

SRC=$( cd "$( dirname "$0" )"; pwd )
DST="${SERVER01}:/opt/"

rsync -rtvP --delete --exclude=.git* ${SRC} ${DST}

pass webdev/server01-chris | head -n1 | ssh -tt ${SERVER01} "sudo systemctl restart dtr5.service"

